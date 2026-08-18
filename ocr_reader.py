import os
from collections import defaultdict

import cv2
import numpy as np
import pytesseract
from PIL import Image, ImageDraw, ImageFont
from pytesseract import Output

from translator import TextTranslator


class OCRReader:
    def __init__(
        self,
        lang="eng",
        target_language="tr",
        translate=True,
        min_confidence=55,
    ):
        self.lang = lang
        self.min_confidence = max(0.0, min(100.0, float(min_confidence)))
        self.translator = TextTranslator(target_language, enabled=translate)
        self.font = self._load_font(18)
        self.tesseract_path = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
        self.available = self._setup_tesseract()

    @staticmethod
    def _load_font(size):
        font_paths = (
            r"C:\Windows\Fonts\arial.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        )
        for font_path in font_paths:
            if os.path.exists(font_path):
                return ImageFont.truetype(font_path, size)
        return ImageFont.load_default()

    def _setup_tesseract(self):
        if os.path.exists(self.tesseract_path):
            pytesseract.pytesseract.tesseract_cmd = self.tesseract_path
            return True

        print("UYARI: Tesseract bulunamadi.")
        return False

    def preprocess(self, frame):
        """Kucuk kamera metinleri icin iki OCR goruntusu hazirla."""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)

        scale = 2.0
        enlarged = cv2.resize(
            enhanced,
            None,
            fx=scale,
            fy=scale,
            interpolation=cv2.INTER_CUBIC,
        )
        blurred = cv2.GaussianBlur(enlarged, (3, 3), 0)
        _, otsu = cv2.threshold(
            blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU
        )
        return ((enlarged, scale), (otsu, scale))

    def preprocess_fast(self, frame):
        """Canli web akisi icin tek gecisli, dusuk maliyetli on isleme."""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        scale = 1.25
        enlarged = cv2.resize(
            gray,
            None,
            fx=scale,
            fy=scale,
            interpolation=cv2.INTER_LINEAR,
        )
        return ((enlarged, scale),)

    def _read_data(self, image):
        return pytesseract.image_to_data(
            image,
            lang=self.lang,
            config="--psm 11 --oem 3 -c preserve_interword_spaces=1",
            output_type=Output.DICT,
        )

    @staticmethod
    def _data_score(data):
        score = 0.0
        for text, confidence in zip(data["text"], data["conf"]):
            text = text.strip()
            try:
                confidence = float(confidence)
            except (TypeError, ValueError):
                continue
            if text and confidence >= 35 and any(char.isalnum() for char in text):
                score += confidence * max(1, len(text))
        return score

    def _is_valid_line(self, words, line_text):
        compact_text = "".join(char for char in line_text if not char.isspace())
        alnum_count = sum(char.isalnum() for char in compact_text)
        if not compact_text or alnum_count == 0:
            return False

        # Kenar, desen ve logolardan gelen noktalama agirlikli sonuclari ele.
        if alnum_count / len(compact_text) < 0.65:
            return False

        weights = [max(1, sum(char.isalnum() for char in word["text"])) for word in words]
        weighted_confidence = sum(
            word["confidence"] * weight for word, weight in zip(words, weights)
        ) / sum(weights)

        if weighted_confidence < self.min_confidence:
            return False

        # Tek karakterli ve kisa rastgele sonuclar ancak cok eminse kabul edilir.
        if alnum_count < 3 and weighted_confidence < 85:
            return False

        return True

    def read(self, frame, synchronous_translation=False, fast=False):
        if not self.available:
            return []

        candidates = []
        prepared_images = self.preprocess_fast(frame) if fast else self.preprocess(frame)
        for processed, scale in prepared_images:
            data = self._read_data(processed)
            candidates.append((self._data_score(data), data, scale))

        _, data, scale = max(candidates, key=lambda candidate: candidate[0])
        lines = defaultdict(list)

        for i, raw_text in enumerate(data["text"]):
            text = raw_text.strip()
            try:
                confidence = float(data["conf"][i])
            except (TypeError, ValueError):
                confidence = -1

            if not text or confidence < 35 or not any(char.isalnum() for char in text):
                continue

            key = (
                data["block_num"][i],
                data["par_num"][i],
                data["line_num"][i],
            )
            lines[key].append(
                {
                    "text": text,
                    "x": int(data["left"][i] / scale),
                    "y": int(data["top"][i] / scale),
                    "w": int(data["width"][i] / scale),
                    "h": int(data["height"][i] / scale),
                    "confidence": confidence,
                }
            )

        result = []
        for words in lines.values():
            words.sort(key=lambda item: item["x"])
            line_text = " ".join(word["text"] for word in words)
            if not self._is_valid_line(words, line_text):
                continue
            x1 = min(word["x"] for word in words)
            y1 = min(word["y"] for word in words)
            x2 = max(word["x"] + word["w"] for word in words)
            y2 = max(word["y"] + word["h"] for word in words)
            result.append({"text": line_text, "box": (x1, y1, x2, y2)})

        return self.translator.translate_lines(
            result, synchronous=synchronous_translation
        )

    def draw_result(self, frame, lines):
        labels = []
        for line in lines:
            x1, y1, x2, y2 = line["box"]
            text = line.get("translated_text", line["text"])
            cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 160, 0), 2)

            language = line.get("detected_language", "unknown")
            target = line.get("target_language", "")
            if line.get("translation_enabled") and target:
                prefix = f"[{language}->{target}] "
            else:
                prefix = f"[{language}] "
            labels.append((x1, max(0, y1 - 25), prefix + text))

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        image = Image.fromarray(rgb)
        drawer = ImageDraw.Draw(image)
        for x, y, text in labels:
            bbox = drawer.textbbox((x, y), text, font=self.font)
            drawer.rectangle(
                (bbox[0] - 3, bbox[1] - 2, bbox[2] + 3, bbox[3] + 2),
                fill=(20, 20, 20),
            )
            drawer.text((x, y), text, font=self.font, fill=(0, 190, 255))

        frame[:] = cv2.cvtColor(np.asarray(image), cv2.COLOR_RGB2BGR)
        return frame

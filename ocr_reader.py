import os
from collections import defaultdict

import cv2
import pytesseract
from pytesseract import Output


class OCRReader:

    def __init__(self, lang="eng"):
        self.lang = lang

        self.tesseract_path = (
            r"C:\Program Files\Tesseract-OCR\tesseract.exe"
        )

        self.available = self._setup_tesseract()

    def _setup_tesseract(self):

        if os.path.exists(self.tesseract_path):
            pytesseract.pytesseract.tesseract_cmd = self.tesseract_path
            return True

        print("UYARI: Tesseract bulunamadi.")
        return False

    def preprocess(self, frame):
        # Griye çevir
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Contrast Enhancement (CLAHE)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        gray = clahe.apply(gray)
        
        # Gaussian Blur (noise reduction)
        gray = cv2.GaussianBlur(gray, (3, 3), 0)
        
        # Bilateral Filter (kenarları koruyarak yumuşat)
        gray = cv2.bilateralFilter(gray, 9, 75, 75)
        
        # Adaptive Thresholding (daha iyi sonuç)
        binary = cv2.adaptiveThreshold(
            gray, 255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            11, 2
        )
        
        return binary

    def read(self, frame):

        if not self.available:
            return []

        processed = self.preprocess(frame)

        data = pytesseract.image_to_data(
            processed,
            lang=self.lang,
            config="--psm 3 --oem 3",
            output_type=Output.DICT
        )

        lines = defaultdict(list)

        for i, raw_text in enumerate(data["text"]):

            text = raw_text.strip()

            try:
                confidence = float(data["conf"][i])
            except ValueError:
                confidence = -1

            if not text or confidence < 40:
                continue

            key = (
                data["block_num"][i],
                data["par_num"][i],
                data["line_num"][i]
            )

            lines[key].append({
                "text": text,
                "x": data["left"][i],
                "y": data["top"][i],
                "w": data["width"][i],
                "h": data["height"][i],
                "confidence": confidence
            })

        result = []

        for words in lines.values():

            # Kelimeleri soldan sağa sırala
            words.sort(
                key=lambda item: item["x"]
            )

            line_text = " ".join(
                word["text"]
                for word in words
            )

            x1 = min(
                word["x"]
                for word in words
            )

            y1 = min(
                word["y"]
                for word in words
            )

            x2 = max(
                word["x"] + word["w"]
                for word in words
            )

            y2 = max(
                word["y"] + word["h"]
                for word in words
            )

            result.append({
                "text": line_text,
                "box": (x1, y1, x2, y2)
            })

        return result

    def draw_result(self, frame, lines):

        for line in lines:

            x1, y1, x2, y2 = line["box"]
            text = line["text"]

            cv2.rectangle(
                frame,
                (x1, y1),
                (x2, y2),
                (255, 160, 0),
                2
            )

            cv2.putText(
                frame,
                text,
                (x1, max(25, y1 - 8)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.55,
                (255, 160, 0),
                2,
                cv2.LINE_AA
            )

        return frame
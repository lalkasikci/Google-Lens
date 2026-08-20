from functools import lru_cache
from queue import Queue
from threading import Thread
from deep_translator import GoogleTranslator
from langdetect import DetectorFactory, LangDetectException, detect

DetectorFactory.seed = 0
class TextTranslator:

    def __init__(self, target_language="tr", enabled=True):
        self.target_language = target_language.lower()
        self.enabled = enabled
        self._warned = False
        self._translations = {}
        self._pending = set()
        self._queue = Queue()
        if enabled:
            Thread(target=self._translation_worker, daemon=True).start()

    @staticmethod
    @lru_cache(maxsize=256)
    def detect_language(text):
        try:
            return detect(text) if text.strip() else "unknown"
        except LangDetectException:
            return "unknown"

    @lru_cache(maxsize=1024)
    def _translate(self, text):
        return GoogleTranslator(
            source="auto",
            target=self.target_language,
        ).translate(text)

    def _translation_worker(self):
        while True:
            text = self._queue.get()
            try:
                self._translations[text] = self._translate(text)
            except Exception as exc:
                self._translations[text] = text
                if not self._warned:
                    print(f"UYARI: Metin cevrilemedi: {exc}")
                    self._warned = True
            finally:
                self._pending.discard(text)
                self._queue.task_done()

    def translate_lines(self, lines, synchronous=False):
        if not lines:
            return lines

        combined_text = " ".join(line["text"] for line in lines)
        detected_language = self.detect_language(combined_text)

        for line in lines:
            source_text = line["text"]
            line["source_text"] = source_text
            line["detected_language"] = detected_language
            line["target_language"] = self.target_language
            line["translation_enabled"] = self.enabled

            if not self.enabled or detected_language == self.target_language:
                line["translated_text"] = source_text
                continue

            if synchronous:
                try:
                    translated = self._translate(source_text)
                    self._translations[source_text] = translated
                    line["translated_text"] = translated
                except Exception as exc:
                    line["translated_text"] = source_text
                    if not self._warned:
                        print(f"UYARI: Metin cevrilemedi: {exc}")
                        self._warned = True
                continue

            line["translated_text"] = self._translations.get(source_text, source_text)
            if source_text not in self._translations and source_text not in self._pending:
                self._pending.add(source_text)
                self._queue.put(source_text)

        return lines

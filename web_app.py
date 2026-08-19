import base64
from functools import lru_cache
from threading import Lock

import cv2
import numpy as np
from flask import Flask, jsonify, render_template, request

from detector import ObjectDetector
from ocr_reader import OCRReader


app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024
processing_lock = Lock()


@lru_cache(maxsize=12)
def get_reader(ocr_language, target_language, confidence):
    return OCRReader(
        lang=ocr_language,
        target_language=target_language,
        translate=True,
        min_confidence=confidence,
    )


@lru_cache(maxsize=1)
def get_detector():
    # YOLO yalnızca nesne algılama ilk kez istendiğinde yüklenir.
    return ObjectDetector(model_name="yolo11s.pt")


@app.get("/")
def index():
    return render_template("index.html")


@app.post("/api/process")
def process_image():
    uploaded = request.files.get("image")
    if uploaded is None or not uploaded.filename:
        return jsonify({"error": "Bir görsel seçmelisiniz."}), 400

    raw = np.frombuffer(uploaded.read(), dtype=np.uint8)
    frame = cv2.imdecode(raw, cv2.IMREAD_COLOR)
    if frame is None:
        return jsonify({"error": "Görsel okunamadı."}), 400

    ocr_language = request.form.get("ocr_language", "eng").strip() or "eng"
    target_language = request.form.get("target_language", "tr").strip() or "tr"
    detect_objects = request.form.get("detect_objects", "true").lower() == "true"
    detect_text = request.form.get("detect_text", "true").lower() == "true"
    live_mode = request.form.get("live", "false").lower() == "true"
    try:
        confidence = max(0.0, min(100.0, float(request.form.get("confidence", 55))))
    except ValueError:
        confidence = 55.0

    try:
        with processing_lock:
            annotated = frame.copy()
            processing_device = "CPU"
            detections = []
            if detect_objects:
                detector = get_detector()
                detections = detector.detect(
                    annotated, image_size=320 if live_mode else 640
                )
                if not live_mode:
                    annotated = detector.draw_detections(annotated, detections)
                processing_device = detector.get_gpu_stats()["device"]
            lines = []
            if detect_text:
                reader = get_reader(ocr_language, target_language, confidence)
                lines = reader.read(
                    frame,
                    synchronous_translation=not live_mode,
                    fast=live_mode,
                )
                if not live_mode:
                    annotated = reader.draw_result(annotated, lines)
    except Exception as exc:
        return jsonify({"error": f"İşlem tamamlanamadı: {exc}"}), 500

    response_lines = [
        {
            "original": line.get("source_text", line["text"]),
            "translated": line.get("translated_text", line["text"]),
            "detected_language": line.get("detected_language", "unknown"),
            "box": list(line["box"]),
        }
        for line in lines
    ]

    image_data = None
    if not live_mode:
        ok, encoded = cv2.imencode(
            ".jpg", annotated, [cv2.IMWRITE_JPEG_QUALITY, 90]
        )
        if not ok:
            return jsonify({"error": "Sonuç görseli oluşturulamadı."}), 500
        image_data = "data:image/jpeg;base64," + base64.b64encode(encoded).decode("ascii")

    return jsonify(
        {
            "lines": response_lines,
            "detections": detections,
            "count": len(response_lines),
            "device": processing_device,
            "frame_width": int(frame.shape[1]),
            "frame_height": int(frame.shape[0]),
            "image": image_data,
        }
    )


@app.errorhandler(413)
def image_too_large(_error):
    return jsonify({"error": "Görsel en fazla 10 MB olabilir."}), 413


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)

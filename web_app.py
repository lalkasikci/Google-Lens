import base64
from functools import lru_cache

import cv2
import numpy as np
from flask import Flask, jsonify, render_template, request

from ocr_reader import OCRReader


app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024


@lru_cache(maxsize=12)
def get_reader(ocr_language, target_language, confidence):
    return OCRReader(
        lang=ocr_language,
        target_language=target_language,
        translate=True,
        min_confidence=confidence,
    )


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
    try:
        confidence = max(0.0, min(100.0, float(request.form.get("confidence", 55))))
    except ValueError:
        confidence = 55.0

    try:
        reader = get_reader(ocr_language, target_language, confidence)
        lines = reader.read(frame, synchronous_translation=True)
        annotated = reader.draw_result(frame.copy(), lines)
    except Exception as exc:
        return jsonify({"error": f"İşlem tamamlanamadı: {exc}"}), 500

    ok, encoded = cv2.imencode(".jpg", annotated, [cv2.IMWRITE_JPEG_QUALITY, 90])
    if not ok:
        return jsonify({"error": "Sonuç görseli oluşturulamadı."}), 500

    response_lines = [
        {
            "original": line.get("source_text", line["text"]),
            "translated": line.get("translated_text", line["text"]),
            "detected_language": line.get("detected_language", "unknown"),
        }
        for line in lines
    ]
    return jsonify(
        {
            "lines": response_lines,
            "count": len(response_lines),
            "image": "data:image/jpeg;base64,"
            + base64.b64encode(encoded).decode("ascii"),
        }
    )


@app.errorhandler(413)
def image_too_large(_error):
    return jsonify({"error": "Görsel en fazla 10 MB olabilir."}), 413


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)

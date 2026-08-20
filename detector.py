import cv2
import torch
from ultralytics import YOLO

class ObjectDetector:
    def __init__(self, model_name="yolo11s.pt", confidence=0.30, device="auto"):
        if device == "auto":
            self.device = 0 if torch.cuda.is_available() else "cpu"
        else:
            self.device = device
        
        self.model = YOLO(model_name)
        self.model.to(self.device)
        self.confidence = confidence
        self._warmup()
        self._print_gpu_info()

    def _warmup(self):
        import numpy as np
        dummy = np.zeros((640, 640, 3), dtype=np.uint8)
        self.model.predict(dummy, conf=self.confidence, verbose=False)
    
    def _print_gpu_info(self):
        if self.device == "cpu":
            print("Çalışma Modu: CPU")
        else:
            print("GPU Modu Aktif")
    
    def get_gpu_stats(self):
        if self.device == "cpu":
            return {
                "device": "CPU",
            }
        
        return {
            "device": "GPU",
        }
    
    def detect(self, frame, image_size=640):
        results = self.model.predict(
            frame,
            conf=self.confidence,
            imgsz=image_size,
            verbose=False,
            device=self.device,
            iou=0.45,
            quantize=16 if self.device != "cpu" else None,
            max_det=50,
        )

        result = results[0]
        names = result.names
        detections = []

        for box in result.boxes:
            x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
            class_id = int(box.cls[0])
            score = float(box.conf[0])
            detections.append({
                "box": [x1, y1, x2, y2],
                "class_name": names[class_id],
                "confidence": score,
                "label": f"{names[class_id]} {score:.0%}",
            })

        return detections

    def detect_and_draw(self, frame, image_size=640):
        detections = self.detect(frame, image_size=image_size)
        return self.draw_detections(frame, detections)

    def draw_detections(self, frame, detections):
        for detection in detections:
            x1, y1, x2, y2 = detection["box"]
            cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 140, 0), 2)
            cv2.putText(
                frame,
                detection["label"],
                (x1, max(25, y1 - 8)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (255, 140, 0),
                2,
                cv2.LINE_AA,
            )
        return frame

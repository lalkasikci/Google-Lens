import cv2
import torch
from ultralytics import YOLO


class ObjectDetector:
    def __init__(self, model_name="yolo11s.pt", confidence=0.30, device="auto"):
        # GPU otomatik algılaması
        if device == "auto":
            self.device = 0 if torch.cuda.is_available() else "cpu"
        else:
            self.device = device
        
        self.model = YOLO(model_name)
        self.model.to(self.device)
        self.confidence = confidence
        
        # İlk çalıştırmada modeli ısıt (GPU memory allocation)
        self._warmup()
        
        # GPU bilgisini logla
        self._print_gpu_info()

    def _warmup(self):
        """GPU'yu ısıt - ilk çalıştırmada daha hızlı olur"""
        import numpy as np
        dummy = np.zeros((640, 640, 3), dtype=np.uint8)
        self.model.predict(dummy, conf=self.confidence, verbose=False)
    
    def _print_gpu_info(self):
        """GPU bilgisini yazdır"""
        if self.device == "cpu":
            print("\n🖥️  Çalışma Modu: CPU")
        else:
            print(f"\n🎮 GPU Modu Aktif!")
            props = torch.cuda.get_device_properties(self.device)
            print(f"   GPU: {props.name}")
            print(f"   VRAM: {props.total_memory / 1e9:.1f} GB")
            print(f"   CUDA Version: {torch.version.cuda}\n")
    
    def get_gpu_stats(self):
        """GPU kullanım istatistiklerini döndür (dictionary)"""
        if self.device == "cpu":
            return {
                "device": "CPU",
                "memory_used": 0,
                "memory_total": 0,
                "memory_percent": 0
            }
        
        allocated = torch.cuda.memory_allocated(self.device) / 1e9
        total = torch.cuda.get_device_properties(self.device).total_memory / 1e9
        percent = (allocated / total * 100) if total > 0 else 0
        
        return {
            "device": "GPU",
            "memory_used": allocated,
            "memory_total": total,
            "memory_percent": percent
        }
    
    def detect_and_draw(self, frame, image_size=640):
        results = self.model.predict(
            frame,
            conf=self.confidence,
            imgsz=image_size,
            verbose=False,
            device=self.device,
            iou=0.45
        )

        result = results[0]
        names = result.names

        for box in result.boxes:
            x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
            class_id = int(box.cls[0])
            score = float(box.conf[0])
            label = f"{names[class_id]} {score:.0%}"

            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 220, 0), 2)
            cv2.putText(
                frame,
                label,
                (x1, max(25, y1 - 8)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0, 220, 0),
                2,
                cv2.LINE_AA,
            )

        return frame

import argparse
from pathlib import Path
import time

import cv2

from detector import ObjectDetector
from ocr_reader import OCRReader
from image_utils import draw_status_bar, resize_keep_ratio


MODE_NAMES = {
    1: "Normal",
    2: "Nesne Tanima",
    3: "Metin Okuma",
    4: "Lens (Nesne + Metin)",
}


def parse_args():
    parser = argparse.ArgumentParser(description="Mini Google Lens - OpenCV + YOLO + OCR")
    parser.add_argument("--image", type=str, default=None, help="Kamera yerine bir resim dosyasi ac")
    parser.add_argument("--camera", type=int, default=0, help="Kamera numarasi (varsayilan: 0)")
    parser.add_argument("--lang", type=str, default="eng", help="Tesseract dili. Ornek: eng veya tur+eng")
    parser.add_argument("--target-lang", type=str, default="tr", help="Ceviri hedef dili. Ornek: tr, en, de, fr")
    parser.add_argument("--no-translate", action="store_true", help="Dil algilamayi koru, ceviriyi kapat")
    parser.add_argument("--ocr-confidence", type=float, default=55, help="OCR guven esigi, 0-100 (varsayilan: 55)")
    parser.add_argument("--device", type=str, default="auto", help="GPU device (0, 1, ... veya 'cpu'). Varsayilan: auto (GPU varsa kullan)")
    return parser.parse_args()


def process_frame(frame, mode, detector, ocr, cached_text_result=None):
    result = frame.copy()

    if mode in (2, 4):
        result = detector.detect_and_draw(result)

    if mode in (3, 4) and cached_text_result is not None:
        result = ocr.draw_result(result, cached_text_result)

    return result


def run_image_mode(image_path, detector, ocr):
    image = cv2.imread(image_path)
    if image is None:
        raise FileNotFoundError(f"Resim acilamadi: {image_path}")

    image = resize_keep_ratio(image, max_width=1200, max_height=800)
    mode = 4
    text_result = ocr.read(image)

    while True:
        shown = process_frame(image, mode, detector, ocr, text_result)
        cv2.imshow("Mini Google Lens", shown)

        key = cv2.waitKey(0) & 0xFF
        if key in (ord("q"), 27):
            break
        elif key in (ord("1"), ord("2"), ord("3"), ord("4")):
            mode = int(chr(key))
            if mode in (3, 4):
                text_result = ocr.read(image)
        elif key == ord("s"):
            save_frame(shown)

    cv2.destroyAllWindows()


def run_camera_mode(camera_index, detector, ocr):
    cap = cv2.VideoCapture(camera_index)
    if not cap.isOpened():
        raise RuntimeError("Kamera acilamadi. --camera 1 gibi farkli bir kamera numarasi deneyebilirsin.")

    mode = 4
    frame_count = 0
    cached_text_result = None
    last_ocr_time = 0.0

    while True:
        ok, frame = cap.read()
        if not ok:
            break

        frame = resize_keep_ratio(frame, max_width=1000, max_height=700)
        frame_count += 1

        # OCR her karede calisirsa kamera cok yavaslar.
        # Bu nedenle yaklasik 0.8 saniyede bir yeniliyoruz.
        if mode in (3, 4) and time.time() - last_ocr_time > 0.8:
            cached_text_result = ocr.read(frame)
            last_ocr_time = time.time()

        shown = process_frame(frame, mode, detector, ocr, cached_text_result)
        shown = draw_status_bar(shown, MODE_NAMES[mode])
        cv2.imshow("Mini Google Lens", shown)

        key = cv2.waitKey(1) & 0xFF
        if key in (ord("q"), 27):
            break
        elif key in (ord("1"), ord("2"), ord("3"), ord("4")):
            mode = int(chr(key))
            cached_text_result = None
        elif key == ord("s"):
            save_frame(shown)

    cap.release()
    cv2.destroyAllWindows()


def save_frame(frame):
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    filename = output_dir / f"lens_{int(time.time())}.jpg"
    cv2.imwrite(str(filename), frame)
    print(f"Kaydedildi: {filename}")


def main():
    args = parse_args()

    print("Model yukleniyor...")
    detector = ObjectDetector(device=args.device)
    ocr = OCRReader(
        lang=args.lang,
        target_language=args.target_lang,
        translate=not args.no_translate,
        min_confidence=args.ocr_confidence,
    )

    print("\nTuslar:")
    print("1 = Kamera")
    print("2 = Nesne tanima")
    print("3 = Metin okuma")
    print("4 = Lens modu")
    print(f"Ceviri hedefi: {args.target_lang}" + (" (kapali)" if args.no_translate else ""))
    print("s = Ekrani kaydet")
    print("q veya ESC = Cikis\n")

    if args.image:
        run_image_mode(args.image, detector, ocr)
    else:
        run_camera_mode(args.camera, detector, ocr)


if __name__ == "__main__":
    main()

import cv2

def resize_keep_ratio(image, max_width=1000, max_height=700):
    height, width = image.shape[:2]
    scale = min(max_width / width, max_height / height, 1.0)

    if scale == 1.0:
        return image

    new_size = (int(width * scale), int(height * scale))
    return cv2.resize(image, new_size, interpolation=cv2.INTER_AREA)


def draw_status_bar(frame, mode_name):
    result = frame.copy()
    height, width = result.shape[:2]

    cv2.rectangle(result, (0, 0), (width, 42), (20, 20, 20), -1)
    text = f"Mod: {mode_name} | 1 Normal  2 Nesne  3 Metin  4 Lens  S Kaydet  Q Cikis"
    cv2.putText(
        result,
        text,
        (12, 28),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.55,
        (240, 240, 240),
        1,
        cv2.LINE_AA,
    )
    return result


def draw_gpu_stats(frame, detector, fps=0):
    """GPU istatistiklerini ve FPS'i çiz"""
    result = frame.copy()
    height, width = result.shape[:2]
    
    gpu_stats = detector.get_gpu_stats()
    
    # Sağ üst köşeye bilgi paneli
    panel_height = 80
    cv2.rectangle(result, (width - 220, 0), (width, panel_height), (20, 20, 20), -1)
    
    # Device bilgisi
    device_color = (0, 220, 0) if gpu_stats["device"] == "GPU" else (100, 100, 100)
    device_icon = "🎮" if gpu_stats["device"] == "GPU" else "🖥️"
    
    cv2.putText(
        result,
        f"{gpu_stats['device']}",
        (width - 210, 25),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.6,
        device_color,
        2,
        cv2.LINE_AA,
    )
    
    # VRAM bilgisi
    if gpu_stats["device"] == "GPU":
        mem_text = f"VRAM: {gpu_stats['memory_used']:.2f}/{gpu_stats['memory_total']:.1f}GB"
        cv2.putText(
            result,
            mem_text,
            (width - 210, 50),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.45,
            (255, 200, 0),
            1,
            cv2.LINE_AA,
        )
        
        # VRAM yüzde göstergesi
        percent_bar_width = 100
        percent_bar_x = width - 210
        percent_bar_y = 65
        
        cv2.rectangle(result, (percent_bar_x, percent_bar_y), 
                     (percent_bar_x + percent_bar_width, percent_bar_y + 8), 
                     (50, 50, 50), -1)
        
        fill_width = int(percent_bar_width * gpu_stats["memory_percent"] / 100)
        color = (0, 220, 0) if gpu_stats["memory_percent"] < 80 else (0, 100, 255)
        
        cv2.rectangle(result, (percent_bar_x, percent_bar_y), 
                     (percent_bar_x + fill_width, percent_bar_y + 8), 
                     color, -1)
        
        cv2.putText(
            result,
            f"{gpu_stats['memory_percent']:.0f}%",
            (percent_bar_x + 105, percent_bar_y + 10),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.35,
            (200, 200, 200),
            1,
            cv2.LINE_AA,
        )
    
  
    if fps > 0:
        cv2.putText(
            result,
            f"FPS: {fps:.1f}",
            (width - 100, 25),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (0, 255, 0),
            2,
            cv2.LINE_AA,
        )
    
    return result

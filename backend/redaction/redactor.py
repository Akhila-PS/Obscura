# redaction/redactor.py


import cv2
import numpy as np
from typing import List, Tuple

DEFAULT_BLUR_STRENGTH = 51
MAX_BLUR_STRENGTH = 201
MIN_BLUR_SIZE = 5



def redact_polygon(img: np.ndarray, pts: list,
                   color: Tuple[int, int, int] = (0, 0, 0)) -> np.ndarray:
    pts_array = np.array(pts, dtype=np.int32)
    cv2.fillPoly(img, [pts_array], color)
    return img


def redact_boxes(img: np.ndarray,
                 boxes: List[List[List[int]]],
                 color: Tuple[int, int, int] = (0, 0, 0),
                 partial: bool = False) -> np.ndarray:
    """
    Redact bounding boxes. Supports partial redaction (e.g., showing last 4 digits).
    """

    if not boxes:
        return img

    for box in boxes:
        # Convert to numpy array of coordinates
        pts_array = np.array(box, dtype=np.int32)
        
        if partial:
            # For partial redaction, we only black out the left ~70% of the bounding box
            x_coords = pts_array[:, 0]
            y_coords = pts_array[:, 1]
            
            x_min, x_max = np.min(x_coords), np.max(x_coords)
            y_min, y_max = np.min(y_coords), np.max(y_coords)
            
            width = x_max - x_min
            # Redact the first 70% of the width
            redact_width = int(width * 0.7)
            
            partial_box = [
                (x_min, y_min),
                (x_min + redact_width, y_min),
                (x_min + redact_width, y_max),
                (x_min, y_max)
            ]
            redact_polygon(img, partial_box, color)
        else:
            # Full redaction
            pts = [(int(x), int(y)) for x, y in box]
            redact_polygon(img, pts, color)

    msg = "Partially" if partial else "Fully"
    print(f"✅ {msg} redacted {len(boxes)} boxes")
    return img




def blur_boxes(img: np.ndarray,
               boxes: List[List[List[int]]],
               blur_strength: int = DEFAULT_BLUR_STRENGTH) -> np.ndarray:

    if blur_strength % 2 == 0:
        blur_strength += 1

    blur_strength = min(blur_strength, MAX_BLUR_STRENGTH)

    for box in boxes:
        x_coords = [int(p[0]) for p in box]
        y_coords = [int(p[1]) for p in box]

        x, y = min(x_coords), min(y_coords)
        x2, y2 = max(x_coords), max(y_coords)

        w, h = x2 - x, y2 - y

        if w < MIN_BLUR_SIZE or h < MIN_BLUR_SIZE:
            continue

        roi = img[y:y+h, x:x+w]
        img[y:y+h, x:x+w] = cv2.GaussianBlur(roi, (blur_strength, blur_strength), 0)

    print(f"✅ Blurred {len(boxes)} boxes")
    return img




def add_watermark(img: np.ndarray,
                  text: str = "REDACTED - NOT FOR OFFICIAL USE") -> np.ndarray:

    h, w = img.shape[:2]
    font = cv2.FONT_HERSHEY_SIMPLEX

    (tw, th), _ = cv2.getTextSize(text, font, 0.7, 2)

    x = (w - tw) // 2
    y = h - 20

    cv2.putText(img, text, (x, y), font, 0.7, (255, 255, 255), 2, cv2.LINE_AA)

    return img

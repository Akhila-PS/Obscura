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
                 color: Tuple[int, int, int] = (0, 0, 0)) -> np.ndarray:
    """
    FULL REDACTION ONLY
    """

    if not boxes:
        return img

    for box in boxes:
        pts = [(int(x), int(y)) for x, y in box]
        redact_polygon(img, pts, color)

    print(f"✅ Fully redacted {len(boxes)} boxes")
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

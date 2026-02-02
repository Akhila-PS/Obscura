# redaction/redactor.py
import cv2
import numpy as np


def redact_polygon(img: np.ndarray, pts: list, color=(0, 0, 0)) -> None:
    """
    Fill a polygon (bounding box) on the image with the given color.
    
    Args:
        img: Image to redact (modified in place)
        pts: List of points [(x1,y1), (x2,y2), (x3,y3), (x4,y4)]
        color: RGB color tuple (default: black)
    """
    pts_array = np.array(pts, dtype=np.int32)
    cv2.fillPoly(img, [pts_array], color)


def redact_boxes(img: np.ndarray, boxes: list, color=(0, 0, 0)) -> np.ndarray:
    """
    Redact multiple bounding boxes on the image.
    
    Args:
        img: Image to redact
        boxes: List of bounding boxes, each is [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
        color: RGB color tuple (default: black)
        
    Returns:
        Modified image with redacted boxes
    """
    for box in boxes:
        if len(box) != 4:
            print(f"⚠️  Skipping invalid box with {len(box)} points: {box}")
            continue
        
        # Convert to integer coordinates
        pts = [(int(x), int(y)) for x, y in box]
        redact_polygon(img, pts, color)
    
    return img
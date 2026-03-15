import cv2
import numpy as np

MIN_OCR_HEIGHT = 1000
MIN_OCR_WIDTH  = 1000


def preprocess_image(path):
    """
    Preprocess an image for EasyOCR.

    Changes vs original:
    - Minimum size raised to 1000px so small ID card photos get a proper
      upscale and small digits become legible.
    - Adaptive threshold replaced with a gentler pipeline:
        1. Upscale if needed (INTER_CUBIC keeps sharpness)
        2. Convert to grayscale
        3. Light Gaussian blur  (noise removal without smearing digits)
        4. CLAHE  (local contrast enhancement — helps faint text on
           coloured / photo backgrounds such as Aadhaar / PAN cards)
        5. Return as grayscale  (EasyOCR accepts single-channel arrays and
           reads them better than harshly binarised images when the source
           has colour gradients or shadows)
    - Scale factors are still tracked correctly so bounding boxes map back
      to original image coordinates.
    """
    img = cv2.imread(path, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Image could not be loaded for OCR preprocessing")

    h, w = img.shape[:2]
    scale_x, scale_y = 1.0, 1.0

    # Upscale small images so OCR can read tiny digits
    if h < MIN_OCR_HEIGHT or w < MIN_OCR_WIDTH:
        scale = max(MIN_OCR_HEIGHT / h, MIN_OCR_WIDTH / w)
        new_w = max(int(w * scale), MIN_OCR_WIDTH)
        new_h = max(int(h * scale), MIN_OCR_HEIGHT)
        img = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_CUBIC)
        scale_x = new_w / w
        scale_y = new_h / h

    # Grayscale
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Mild denoise — kernel (3,3) to avoid blurring digit strokes
    blur = cv2.GaussianBlur(gray, (3, 3), 0)

    # CLAHE: boosts local contrast without destroying colour-card backgrounds
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(blur)

    return enhanced, (scale_x, scale_y)
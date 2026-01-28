import cv2

def preprocess_image(path):
    """
    OCR-only preprocessing.
    Returns a thresholded grayscale image for OCR.
    """

    img = cv2.imread(path, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Image could not be loaded for OCR preprocessing")

    # Ensure minimum size
    h, w = img.shape[:2]
    if h < 300 or w < 300:
        img = cv2.resize(img, (max(w, 300), max(h, 300)), interpolation=cv2.INTER_CUBIC)

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5, 5), 0)

    ocr_image = cv2.adaptiveThreshold(
        blur,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        11,
        2
    )

    return ocr_image

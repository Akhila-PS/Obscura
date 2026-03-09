import cv2

MIN_OCR_HEIGHT = 600
MIN_OCR_WIDTH = 600


def preprocess_image(path):
    
    img = cv2.imread(path, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Image could not be loaded for OCR preprocessing")

    h, w = img.shape[:2]
    scale_x, scale_y = 1.0, 1.0

    if h < MIN_OCR_HEIGHT or w < MIN_OCR_WIDTH:
        scale = max(MIN_OCR_HEIGHT / h, MIN_OCR_WIDTH / w)
        new_w = max(int(w * scale), MIN_OCR_WIDTH)
        new_h = max(int(h * scale), MIN_OCR_HEIGHT)
        img = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_CUBIC)
        scale_x = new_w / w
        scale_y = new_h / h

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5, 5), 0)

    ocr_image = cv2.adaptiveThreshold(
        blur,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        11,
        2,
    )

    return ocr_image, (scale_x, scale_y)

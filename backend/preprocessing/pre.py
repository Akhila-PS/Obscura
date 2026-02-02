import cv2
import numpy as np
from PIL import Image
import pytesseract
from pdf2image import convert_from_bytes
import os

# If on Windows, set Tesseract path
# pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

def preprocess_for_ocr(image):
    """
    image: either a file path to an image, a file-like object, or a NumPy array
    Returns: preprocessed image ready for OCR
    """
    # ---------- LOAD IMAGE ----------
    if hasattr(image, 'content_type') and image.content_type == 'application/pdf':
        # Convert PDF to images (first page only)
        pdf_images = convert_from_bytes(image.read())
        pil_image = pdf_images[0]  # take first page
    elif isinstance(image, str):
        pil_image = Image.open(image)
    elif not isinstance(image, np.ndarray):
        pil_image = Image.open(image)
    else:
        pil_image = Image.fromarray(image)

    # ---------- CONVERT TO OPENCV FORMAT ----------
    img = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)

    # ---------- GRAYSCALE ----------
    if img.ndim == 3:
        img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # ---------- ENHANCE FOR OCR ----------
    # Resize to make small text clearer
    scale = 2
    img = cv2.resize(img, (img.shape[1]*scale, img.shape[0]*scale), interpolation=cv2.INTER_CUBIC)

    # Adaptive threshold to binarize
    img = cv2.adaptiveThreshold(img, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                cv2.THRESH_BINARY, 11, 2)

    # Optional: remove small noise
    img = cv2.medianBlur(img, 3)

    # ---------- DEBUG: SAVE PREPROCESSED IMAGE ----------
    os.makedirs("debug", exist_ok=True)
    debug_path = os.path.join("debug", "ocr_ready.png")
    cv2.imwrite(debug_path, img)
    print(f"[DEBUG] Preprocessed image saved at: {debug_path}")

    return img


def extract_printed_text(image):
    """
    image: file path, file-like object, or NumPy array
    Returns: text extracted by Tesseract
    """
    processed_img = preprocess_for_ocr(image)

    # ---------- OCR ----------
    custom_config = r'--oem 3 --psm 6'  # LSTM OCR, assume uniform block of text
    text = pytesseract.image_to_string(processed_img, config=custom_config)

    # ---------- DEBUG: PRINT OCR OUTPUT ----------
    print("[DEBUG] OCR detected text:")
    print(text)

    return text

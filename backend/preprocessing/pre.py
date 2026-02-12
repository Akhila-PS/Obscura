import cv2
import numpy as np
from PIL import Image
import pytesseract
from pdf2image import convert_from_bytes
import os


def preprocess_for_ocr(image):
   
    if hasattr(image, 'content_type') and image.content_type == 'application/pdf':
        pdf_images = convert_from_bytes(image.read())
        pil_image = pdf_images[0] 
    elif isinstance(image, str):
        pil_image = Image.open(image)
    elif not isinstance(image, np.ndarray):
        pil_image = Image.open(image)
    else:
        pil_image = Image.fromarray(image)

    img = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)

    if img.ndim == 3:
        img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    scale = 2
    img = cv2.resize(img, (img.shape[1]*scale, img.shape[0]*scale), interpolation=cv2.INTER_CUBIC)

    img = cv2.adaptiveThreshold(img, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                cv2.THRESH_BINARY, 11, 2)

    img = cv2.medianBlur(img, 3)

    # DEBUG: SAVE PREPROCESSED IMAGE ----------
    os.makedirs("debug", exist_ok=True)
    debug_path = os.path.join("debug", "ocr_ready.png")
    cv2.imwrite(debug_path, img)
    print(f"[DEBUG] Preprocessed image saved at: {debug_path}")

    return img


def extract_printed_text(image):
   
    processed_img = preprocess_for_ocr(image)

    custom_config = r'--oem 3 --psm 6'  # LSTM OCR, assume uniform block of text
    text = pytesseract.image_to_string(processed_img, config=custom_config)

    print("[DEBUG] OCR detected text:")
    print(text)

    return text

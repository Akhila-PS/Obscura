# redaction/sensitive_detector_image.py
import re

def clean_ocr_text(text: str) -> str:
    """Clean OCR text by fixing common OCR mistakes and removing unwanted characters."""
    text = text.replace("O", "0").replace("o", "0")
    text = text.strip()
    text = re.sub(r'\s+', '', text)  # remove spaces
    text = re.sub(r'[^0-9]', '', text)  # keep only digits (for Aadhaar/Phone)
    return text

def find_aadhaar_boxes(ocr_results):
    boxes = []
    for bbox, text, conf in ocr_results:
        text = clean_ocr_text(text)
        if conf < 0.6:
            continue
        if re.fullmatch(r"\d{12}", text):
            boxes.append(bbox)
    return boxes

def find_phone_boxes(ocr_results):
    boxes = []
    for bbox, text, conf in ocr_results:
        text = clean_ocr_text(text)
        if conf < 0.6:
            continue
        if re.fullmatch(r"[6-9]\d{9}", text):
            boxes.append(bbox)
    return boxes

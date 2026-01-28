import re

# ---------------- CLEAN OCR TEXT ----------------
def clean_ocr_text(text: str) -> str:
    """
    Clean OCR text by fixing common OCR mistakes and removing unwanted characters.
    Keeps only digits for Aadhaar and Phone detection.
    """
    text = text.replace("O", "0").replace("o", "0")
    text = text.strip()
    text = re.sub(r'\s+', '', text)       # remove whitespace
    text = re.sub(r'[^0-9]', '', text)    # keep only digits
    return text


# ---------------- INTERNAL HELPERS ----------------
def extract_digit_stream(ocr_results):
    stream = ""
    box_map = []
    cursor = 0

    for bbox, text, conf in ocr_results:
        digits = clean_ocr_text(text)
        if len(digits) >= 2:
            start = cursor
            stream += digits
            end = cursor + len(digits)
            box_map.append((start, end, bbox))
            cursor = end

    return stream, box_map


def _collect(matches, box_map):
    boxes = set()
    for m in matches:
        for s, e, bbox in box_map:
            if s < m.end() and e > m.start():
                boxes.add(tuple(map(tuple, bbox)))
    return [list(b) for b in boxes]


# ---------------- DETECTION FUNCTIONS ----------------
def find_aadhaar_boxes(ocr_results):
    stream, box_map = extract_digit_stream(ocr_results)
    matches = re.finditer(r"\d{12}", stream)
    return _collect(matches, box_map)


def find_phone_boxes(ocr_results):
    stream, box_map = extract_digit_stream(ocr_results)
    matches = re.finditer(r"[6-9]\d{9}", stream)
    return _collect(matches, box_map)

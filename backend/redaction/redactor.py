import cv2
import numpy as np



# Import detectors for image and PDF
from redaction.sensitive_detector_image import (
    find_aadhaar_boxes as find_img_aadhaar,
    find_phone_boxes as find_img_phone,
    clean_ocr_text
)
from redaction.sensitive_detector_pdf import (
    find_aadhaar_boxes as find_pdf_aadhaar,
    find_phone_boxes as find_pdf_phone
)


# ---------------- BASIC REDACTION ----------------
def redact_polygon(img, pts, color=(0, 0, 0)):
    """Fill a polygon (bounding box) on the image with the given color."""
    pts_array = np.array(pts, dtype=np.int32)
    cv2.fillPoly(img, [pts_array], color)


def redact_boxes(img, boxes, color=(0, 0, 0)):
    """Redact multiple bounding boxes on the image."""
    for box in boxes:
        if len(box) != 4:
            continue  # skip invalid boxes
        pts = [(int(x), int(y)) for x, y in box]
        redact_polygon(img, pts, color)
    return img


# ---------------- OCR-BASED CHECKS ----------------
def should_redact_box(text, labels):
    """Determine if a detected OCR text should be redacted."""
    digits = ''.join(c for c in text if c.isdigit())
    length = len(digits)

    if "Aadhaar" in labels and length == 12:
        return True
    if "Phone Number" in labels and 10 <= length <= 13:
        return True
    if "Credit Card" in labels and length == 16:
        return True
    return False


# ---------------- FULL REDACTION FUNCTION ----------------
def redact_sensitive_text(image_path, ocr_results, source_type="image", output_path=None, color=(0, 0, 0)):
    """
    Redact sensitive data from an image (or PDF page).
    - image_path: path to input image
    - ocr_results: list of (bbox, text, confidence)
    - source_type: "image" or "pdf"
    - output_path: where to save redacted image
    - color: redaction color (default black)
    Returns list of explanations of what was redacted.
    """
    img = cv2.imread(image_path)
    if img is None:
        raise ValueError(f"Failed to read image: {image_path}")

    explanations = []

    # ---------------- DETECTION ----------------
    if source_type == "pdf":
        aadhaar_boxes = find_pdf_aadhaar(ocr_results)
        phone_boxes = find_pdf_phone(ocr_results)
    else:
        aadhaar_boxes = find_img_aadhaar(ocr_results)
        phone_boxes = find_img_phone(ocr_results)

    # ---------------- REDACTION ----------------
    img = redact_boxes(img, aadhaar_boxes, color)
    explanations.extend(["Aadhaar detected"] * len(aadhaar_boxes))

    img = redact_boxes(img, phone_boxes, color)
    explanations.extend(["Phone number detected"] * len(phone_boxes))

    # ---------------- OCR-BASED EXTRA REDACTION ----------------
    for bbox, text, conf in ocr_results:
        if conf < 0.3:
            continue
        clean_text = clean_ocr_text(text)
        if should_redact_box(clean_text, ["Aadhaar"]):
            img = redact_boxes(img, [bbox], color)
            explanations.append("Aadhaar detected via OCR")
        elif should_redact_box(clean_text, ["Phone Number"]):
            img = redact_boxes(img, [bbox], color)
            explanations.append("Phone number detected via OCR")
        elif should_redact_box(clean_text, ["Credit Card"]):
            img = redact_boxes(img, [bbox], color)
            explanations.append("Credit card detected via OCR")

    # ---------------- SAVE ----------------
    if output_path:
        cv2.imwrite(output_path, img)

    return explanations

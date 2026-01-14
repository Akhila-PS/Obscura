import cv2
import numpy as np
from redaction.sensitive_detector import detect

def redact_sensitive_text(image_path, ocr_results, output_path):
    img = cv2.imread(image_path)
    explanations = []

    for bbox, text, conf in ocr_results:
        label = detect(text)
        if label:
            pts = np.array(bbox).astype(int)
            cv2.fillPoly(img, [pts], (0,0,0))
            explanations.append(f"{label} detected and redacted")

    cv2.imwrite(output_path, img)
    return explanations

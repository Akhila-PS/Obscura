import os
import cv2
import base64
import mimetypes
import uuid
from flask import Flask, request, jsonify
from flask_cors import CORS
from werkzeug.utils import secure_filename

from preprocessing.metadata_removal import remove_metadata
from preprocessing.image_cleaner import preprocess_image
from ocr.printed_ocr import extract_printed_text
from redaction.sensitive_detector_image import (
    find_aadhaar_boxes as find_img_aadhaar,
    find_phone_boxes as find_img_phone
)

from redaction.sensitive_detector_pdf import (
    find_aadhaar_boxes as find_pdf_aadhaar,
    find_phone_boxes as find_pdf_phone
)
from redaction.redactor import redact_boxes
from pdf.pdf_to_images import pdf_to_images
from pdf.images_to_pdf import images_to_pdf

app = Flask(__name__)
CORS(app)

UPLOAD_ORIGINAL = "uploads/original"
UPLOAD_REDACTED = "uploads/redacted"
UPLOAD_TEMP = "uploads/temp_pages"

for d in [UPLOAD_ORIGINAL, UPLOAD_REDACTED, UPLOAD_TEMP]:
    os.makedirs(d, exist_ok=True)


# ---------------- IMAGE / PAGE PROCESSING ----------------
def process_image(image_path, output_path, source_type="image"):
    if not os.path.exists(image_path):
        raise ValueError("Uploaded file not found")

    # ---- METADATA REMOVAL ----
    clean_path = image_path + "_clean.png"
    remove_metadata(image_path, clean_path)

    if not os.path.exists(clean_path):
        raise ValueError("Metadata removal failed")

    # ---- OCR PREPROCESS ----
    ocr_ready = preprocess_image(clean_path)
    ocr_results = extract_printed_text(ocr_ready)

    # ---- DETECTION (SEPARATED LOGIC) ----
    if source_type == "pdf":
        # PDF detector
        aadhaar_boxes = find_pdf_aadhaar(ocr_results)
        phone_boxes = find_pdf_phone(ocr_results)
    else:
        # IMAGE detector
        aadhaar_boxes = find_img_aadhaar(ocr_results)
        phone_boxes = find_img_phone(ocr_results)

    # ---- REDACTION ----
    image = cv2.imread(clean_path)
    if image is None:
        raise ValueError("Failed to read cleaned image")

    image = redact_boxes(image, aadhaar_boxes)
    image = redact_boxes(image, phone_boxes)

    cv2.imwrite(output_path, image)

    # ---- RESPONSE ----
    return (
        ["Aadhaar detected"] * len(aadhaar_boxes) +
        ["Phone number detected"] * len(phone_boxes)
    )


# ---------------- UPLOAD ROUTE ----------------
@app.route("/upload", methods=["POST"])
def upload():
    if "image" not in request.files:
        return jsonify({"error": "Form-data key must be 'image'"}), 400

    file = request.files["image"]

    if file.filename == "":
        return jsonify({"error": "Empty filename"}), 400

    filename = secure_filename(file.filename.lower())
    uid = uuid.uuid4().hex
    name, ext = os.path.splitext(filename)

    if not ext:
        return jsonify({"error": "File has no extension"}), 400

    saved_name = f"{name}_{uid}{ext}"
    original_path = os.path.join(UPLOAD_ORIGINAL, saved_name)
    file.save(original_path)

    file_type, _ = mimetypes.guess_type(original_path)

    if not file_type:
        return jsonify({"error": "Unsupported file type"}), 400

    explanations = []

    # ---------------- IMAGE ----------------
    if file_type.startswith("image"):
        output_path = os.path.join(
            UPLOAD_REDACTED,
            f"{name}_{uid}_redacted.png"
        )

        explanations = process_image(
            original_path,
            output_path,
            source_type="image"
        )

        with open(output_path, "rb") as f:
            encoded = base64.b64encode(f.read()).decode()

        return jsonify({
            "type": "image",
            "risk_score": len(explanations) * 20,
            "explanations": explanations,
            "redacted_image": encoded
        })

    # ---------------- PDF ----------------
    if file_type == "application/pdf":
        pages = pdf_to_images(original_path, UPLOAD_TEMP)
        redacted_pages = []

        for page in pages:
            out_page = page.replace(".png", "_redacted.png")
            explanations.extend(
                process_image(page, out_page, source_type="pdf")
            )
            redacted_pages.append(out_page)

        final_pdf = os.path.join(
            UPLOAD_REDACTED,
            f"redacted_{uid}.pdf"
        )

        images_to_pdf(redacted_pages, final_pdf)

        with open(final_pdf, "rb") as f:
            encoded = base64.b64encode(f.read()).decode()

        return jsonify({
            "type": "pdf",
            "risk_score": len(explanations) * 20,
            "explanations": explanations,
            "redacted_pdf": encoded
        })

    return jsonify({"error": "Unsupported format"}), 400


if __name__ == "__main__":
    app.run(debug=True)

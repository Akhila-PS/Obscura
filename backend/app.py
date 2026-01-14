import os
import cv2
import base64
import mimetypes
from flask import Flask, request, jsonify
from flask_cors import CORS

from preprocessing.metadata_removal import remove_metadata
from preprocessing.image_cleaner import preprocess_image
from ocr.printed_ocr import extract_printed_text
from redaction.redactor import redact_sensitive_text
from pdf.pdf_to_images import pdf_to_images
from pdf.images_to_pdf import images_to_pdf

app = Flask(__name__)
CORS(app)

UPLOAD_ORIGINAL = "uploads/original"
UPLOAD_REDACTED = "uploads/redacted"
UPLOAD_TEMP = "uploads/temp_pages"

os.makedirs(UPLOAD_ORIGINAL, exist_ok=True)
os.makedirs(UPLOAD_REDACTED, exist_ok=True)
os.makedirs(UPLOAD_TEMP, exist_ok=True)


@app.route("/upload", methods=["POST"])
def upload():
    if "image" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files["image"]
    filename = file.filename
    file_type = mimetypes.guess_type(filename)[0]

    original_path = os.path.join(UPLOAD_ORIGINAL, filename)
    file.save(original_path)

    explanations = []

    # ================= IMAGE HANDLING =================
    if file_type and file_type.startswith("image"):
        clean_path = original_path.replace(".", "_clean.")
        output_path = os.path.join(UPLOAD_REDACTED, filename)

        remove_metadata(original_path, clean_path)
        processed = preprocess_image(clean_path)
        cv2.imwrite(clean_path, processed)

        ocr_results = extract_printed_text(clean_path)
        explanations = redact_sensitive_text(clean_path, ocr_results, output_path)

        with open(output_path, "rb") as f:
            encoded = base64.b64encode(f.read()).decode()

        return jsonify({
            "type": "image",
            "redacted_image": encoded,
            "risk_score": len(explanations) * 20,
            "explanations": explanations
        })

    # ================= PDF HANDLING =================
    if file_type == "application/pdf":
        pages = pdf_to_images(original_path, UPLOAD_TEMP)
        redacted_pages = []

        for page in pages:
            clean = page.replace(".png", "_clean.png")
            output = page.replace(".png", "_redacted.png")

            remove_metadata(page, clean)
            processed = preprocess_image(clean)
            cv2.imwrite(clean, processed)

            ocr_results = extract_printed_text(clean)
            exp = redact_sensitive_text(clean, ocr_results, output)

            explanations.extend(exp)
            redacted_pages.append(output)

        final_pdf = os.path.join(UPLOAD_REDACTED, "redacted_output.pdf")
        images_to_pdf(redacted_pages, final_pdf)

        with open(final_pdf, "rb") as f:
            encoded = base64.b64encode(f.read()).decode()

        return jsonify({
            "type": "pdf",
            "redacted_pdf": encoded,
            "risk_score": len(explanations) * 20,
            "explanations": explanations
        })

    return jsonify({"error": "Unsupported file format"}), 400


if __name__ == "__main__":
    app.run(debug=True)

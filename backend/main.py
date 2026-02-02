# main.py
import os
import sys
import cv2
import base64
import mimetypes
import uuid
import traceback
import shutil
from flask import Flask, request, jsonify
from flask_cors import CORS
from werkzeug.utils import secure_filename

from preprocessing.metadata_removal import remove_metadata
from preprocessing.image_cleaner import preprocess_image
from ocr.printed_ocr import extract_printed_text
from redaction.sensitive_detector_image import (
    find_aadhaar_boxes,
    find_vid_boxes,
    find_phone_boxes,
)
from redaction.redactor import redact_boxes
from pdf.pdf_to_images import pdf_to_images
from pdf.images_to_pdf import images_to_pdf

app = Flask(__name__)
CORS(app)

# Upload directories
UPLOAD_ORIGINAL = "uploads/original"
UPLOAD_REDACTED = "uploads/redacted"
UPLOAD_TEMP = "uploads/temp_pages"

for d in [UPLOAD_ORIGINAL, UPLOAD_REDACTED, UPLOAD_TEMP]:
    os.makedirs(d, exist_ok=True)


def _scale_ocr_boxes(ocr_results, scale_x, scale_y):
    """Map bbox coordinates from preprocessed (possibly upscaled) image back to original."""
    if scale_x == 1.0 and scale_y == 1.0:
        return ocr_results
    
    scaled = []
    for bbox, text, conf in ocr_results:
        scaled_bbox = [[p[0] / scale_x, p[1] / scale_y] for p in bbox]
        scaled.append((scaled_bbox, text, conf))
    
    return scaled


# ---------------- IMAGE / PAGE PROCESSING ----------------
def process_image(image_path, output_path, source_type="image"):
    """
    Process both images and PDF pages using the SAME logic.
    Uses regex-based detection for all sensitive data.
    """
    if not os.path.exists(image_path):
        raise ValueError(f"File not found: {image_path}")

    # ---- METADATA REMOVAL ----
    clean_path = image_path + "_clean.png"
    remove_metadata(image_path, clean_path)

    if not os.path.exists(clean_path):
        raise ValueError("Metadata removal failed")

    # ---- OCR PREPROCESS ----
    ocr_ready, (scale_x, scale_y) = preprocess_image(clean_path)

    # ---- OCR ----
    ocr_results = extract_printed_text(ocr_ready)
    
    # Scale boxes back to original image coordinates
    ocr_results = _scale_ocr_boxes(ocr_results, scale_x, scale_y)

    # ---- DETECTION (SAME FOR BOTH IMAGE AND PDF) ----
    print(f"\n🔍 Detecting sensitive data in {source_type}...")
    
    aadhaar_boxes = find_aadhaar_boxes(ocr_results)
    vid_boxes = find_vid_boxes(ocr_results)
    phone_boxes = find_phone_boxes(ocr_results)

    # ---- REDACTION ----
    image = cv2.imread(clean_path)
    if image is None:
        raise ValueError(f"Failed to read cleaned image: {clean_path}")

    # Redact all detected boxes
    detection_results = [
        (aadhaar_boxes, "Aadhaar number"),
        (vid_boxes, "VID"),
        (phone_boxes, "Phone number"),
    ]
    
    for boxes, label in detection_results:
        if boxes:
            image = redact_boxes(image, boxes)
            print(f"  ✅ Redacted {len(boxes)} {label}(s)")

    # Save redacted image
    cv2.imwrite(output_path, image)
    print(f"💾 Saved redacted image: {output_path}")

    # ---- EXPLANATIONS ----
    explanations = []
    for boxes, label in detection_results:
        explanations.extend([f"{label} redacted"] * len(boxes))

    return explanations


# ---------------- UPLOAD ROUTE ----------------
@app.route("/upload", methods=["POST"])
def upload():
    try:
        if "image" not in request.files:
            return jsonify({"error": "Form-data key must be 'image'"}), 400

        file = request.files["image"]
        if not file.filename:
            return jsonify({"error": "Empty filename"}), 400

        filename = secure_filename(file.filename.lower())
        uid = uuid.uuid4().hex
        name, ext = os.path.splitext(filename)
        saved_name = f"{name}_{uid}{ext}"
        original_path = os.path.join(UPLOAD_ORIGINAL, saved_name)
        
        # Save uploaded file
        file.save(original_path)
        print(f"\n📤 Received file: {filename} → {saved_name}")

        file_type, _ = mimetypes.guess_type(original_path)
        if not file_type:
            return jsonify({"error": "Unsupported file type"}), 400

        explanations = []

        # ---------------- IMAGE ----------------
        if file_type.startswith("image"):
            print(f"🖼️  Processing as IMAGE")
            output_path = os.path.join(
                UPLOAD_REDACTED,
                f"{name}_{uid}_redacted.png"
            )
            
            explanations = process_image(original_path, output_path, source_type="image")

            with open(output_path, "rb") as f:
                encoded = base64.b64encode(f.read()).decode()

            # Calculate risk score (cap at 100)
            risk_score = min(len(explanations) * 20, 100)

            return jsonify({
                "type": "image",
                "risk_score": risk_score,
                "explanations": explanations,
                "redacted_image": encoded
            })

        # ---------------- PDF ----------------
        elif file_type == "application/pdf":
            print(f"📄 Processing as PDF")
            temp_dir = os.path.join(UPLOAD_TEMP, uid)
            os.makedirs(temp_dir, exist_ok=True)

            try:
                # Convert PDF to images
                pages = pdf_to_images(original_path, temp_dir)
                print(f"📑 PDF has {len(pages)} pages")
                
                redacted_pages = []

                # Process each page
                for i, page in enumerate(pages, 1):
                    print(f"\n--- Processing page {i}/{len(pages)} ---")
                    out_page = page.replace(".png", "_redacted.png")
                    page_explanations = process_image(page, out_page, source_type="pdf")
                    explanations.extend(page_explanations)
                    redacted_pages.append(out_page)

                # Convert back to PDF
                final_pdf = os.path.join(UPLOAD_REDACTED, f"redacted_{uid}.pdf")
                images_to_pdf(redacted_pages, final_pdf)
                print(f"\n✅ Created final PDF: {final_pdf}")

                with open(final_pdf, "rb") as f:
                    encoded = base64.b64encode(f.read()).decode()

                # Calculate risk score (cap at 100)
                risk_score = min(len(explanations) * 20, 100)

                return jsonify({
                    "type": "pdf",
                    "risk_score": risk_score,
                    "explanations": explanations,
                    "redacted_pdf": encoded
                })

            finally:
                # CLEANUP: Remove temporary files
                if os.path.exists(temp_dir):
                    shutil.rmtree(temp_dir, ignore_errors=True)
                    print(f"🗑️  Cleaned up temp directory: {temp_dir}")

        else:
            return jsonify({"error": "Unsupported format (expected image or PDF)"}), 400

    except Exception as e:
        traceback.print_exc(file=sys.stderr)
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    print("🚀 Starting Document Redaction Server...")
    print("📁 Upload directories ready:")
    print(f"   - Original: {UPLOAD_ORIGINAL}")
    print(f"   - Redacted: {UPLOAD_REDACTED}")
    print(f"   - Temp: {UPLOAD_TEMP}")
    app.run(debug=True)
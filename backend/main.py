"""
Integrated Flask backend for both Sensitive Data Redaction and Metadata Redaction
FIXED VERSION - All bugs corrected
"""
import os
import sys
import cv2
import base64
import mimetypes
import uuid
import traceback
import shutil
import json

from flask import Flask, request, jsonify
from flask_cors import CORS
from werkzeug.utils import secure_filename
from PIL import Image, ExifTags

from preprocessing.metadata_removal import remove_metadata
from preprocessing.image_cleaner import preprocess_image

from ocr.printed_ocr import extract_printed_text

from redaction.sensitive_detector_image import (
    find_qr_codes,
    find_faces
)

from redaction.redactor import (
    redact_boxes,
    blur_boxes,
    add_watermark,
)

from pdf.pdf_to_images import pdf_to_images
from pdf.images_to_pdf import images_to_pdf

from redaction.llm_processor import generate_redaction_summary, detect_custom_rules, detect_sensitive_entities_ai


app = Flask(__name__)
CORS(app)

UPLOAD_ORIGINAL = "uploads/original"
UPLOAD_REDACTED = "uploads/redacted"
UPLOAD_TEMP = "uploads/temp_pages"

for d in [UPLOAD_ORIGINAL, UPLOAD_REDACTED, UPLOAD_TEMP]:
    os.makedirs(d, exist_ok=True)


def _scale_ocr_boxes(ocr_results, scale_x, scale_y):
    """
    """
    if scale_x == 1.0 and scale_y == 1.0:
        return ocr_results
    
    scaled = []
    for bbox, text, conf in ocr_results:
        scaled_bbox = [[p[0] / scale_x, p[1] / scale_y] for p in bbox]
        scaled.append((scaled_bbox, text, conf))
    return scaled




def process_image_with_options(image_path, output_path, options, custom_prompt="", source_type="image"):
    """
    Process image with user-selected redaction options and optional custom rules.
    FIXED: Added comprehensive logging and PAN detection
    """
    print(f"\n{'='*70}")
    print(f"🎯 STARTING REDACTION PROCESS - {source_type.upper()}")
    print(f"{'='*70}")
    print(f"📂 Input:  {image_path}")
    print(f"📂 Output: {output_path}")
    print(f"⚙️  Options: {options}")
    
    if not os.path.exists(image_path):
        print(f"❌ ERROR: Input file doesn't exist!")
        raise ValueError(f"File not found: {image_path}")
    
    file_size = os.path.getsize(image_path)
    print(f"✅ Input file exists ({file_size} bytes)")
    
    default_options = {
        "general_pii": True,
        "aadhaar": True,
        "vid": True,
        "pan": True,     # ADDED
        "phone": True,
        "qr": True,
        "face": False,
        "email": False,
        "plate": False,
        "watermark": True,
    }
    
    redaction_opts = {**default_options, **options}
    active_redactions = [k for k, v in redaction_opts.items() if v]
    print(f"\n🔧 Active redactions ({len(active_redactions)}): {', '.join(active_redactions)}")
    
    print(f"\n📋 Step 1: Removing metadata...")
    clean_path = image_path + "_clean.png"
    remove_metadata(image_path, clean_path)
    
    if not os.path.exists(clean_path):
        print(f"❌ ERROR: Metadata removal failed!")
        raise ValueError("Metadata removal failed")
    print(f"✅ Metadata removed, clean image: {clean_path}")
    
    print(f"\n📋 Step 2: Preprocessing for OCR...")
    ocr_ready, (scale_x, scale_y) = preprocess_image(clean_path)
    print(f"✅ Image preprocessed (scale: {scale_x:.2f}x, {scale_y:.2f}y)")
    
    print(f"\n📋 Step 3: Extracting text with OCR...")
    ocr_results = extract_printed_text(ocr_ready)
    print(f"📝 OCR found {len(ocr_results)} text regions")
    
    for i, (bbox, text, conf) in enumerate(ocr_results[:5]):
        print(f"   [{i+1}] '{text}' (confidence: {conf:.2f})")
    if len(ocr_results) > 5:
        print(f"   ... and {len(ocr_results) - 5} more")
    
    ocr_results = _scale_ocr_boxes(ocr_results, scale_x, scale_y)
    print(f"✅ OCR boxes scaled back to original coordinates")
    
    print(f"\n📋 Step 4: Detecting sensitive data...")
    detection_results = []
    
    
    # Vision-based (OpenCV/Haarcascades) detections
    if redaction_opts.get("qr", True):
        print(f"   🔍 Detecting QR codes...")
        qr_boxes = find_qr_codes(clean_path)
        if qr_boxes:
            detection_results.append((qr_boxes, "QR code", "redact"))
            print(f"      ✅ Found {len(qr_boxes)} QR code(s)")
    
    if redaction_opts.get("face", False):
        print(f"   🔍 Detecting faces...")
        face_boxes = find_faces(clean_path)
        if face_boxes:
            detection_results.append((face_boxes, "Face", "blur"))
            print(f"      ✅ Found {len(face_boxes)} face(s)")

    # Text-based (LLM) detections
    # Exclude vision items and custom rules from the list sent to the LLM
    active_text_redactions = [k for k in active_redactions if k not in ["qr", "face", "watermark", "partial"]]

    if active_text_redactions or (custom_prompt and custom_prompt.strip()):
        print(f"   🔍 Detecting text entities via Unified LLM Redaction...")
        
        # We handle text redactions AND custom prompts in a single call now!
        categorized_boxes = detect_sensitive_entities_ai(ocr_results, active_text_redactions, custom_prompt)
        
        for category, boxes in categorized_boxes.items():
            if category == "custom":
                label = "Custom Rule Match"
            elif category == "general_pii":
                label = "General PII (ID/DOB/Expiry)"
            elif category == "aadhaar":
                label = "Aadhaar number"
            elif category == "vid":
                label = "VID"
            elif category == "pan":
                label = "PAN card"
            elif category == "phone":
                label = "Phone number"
            elif category == "email":
                label = "Email address"
            elif category == "plate":
                label = "License plate"
            else:
                label = f"{category.capitalize()}"
                
            detection_results.append((boxes, label, "redact"))
            print(f"      ✅ Found {len(boxes)} {label}(s)")
    
    print(f"\n📊 Detection Summary:")
    if detection_results:
        print(f"   Total types detected: {len(detection_results)}")
        for boxes, label, method in detection_results:
            print(f"   ✓ {label}: {len(boxes)} instance(s) ({method})")
    else:
        print(f"   ⚠️  No sensitive data detected!")
    
    print(f"\n📋 Step 5: Loading image for redaction...")
    image = cv2.imread(clean_path)
    if image is None:
        print(f"❌ ERROR: Failed to load cleaned image!")
        raise ValueError(f"Failed to read cleaned image: {clean_path}")
    
    print(f"✅ Image loaded: {image.shape} (H×W×C)")
    
    print(f"\n📋 Step 6: Applying redactions...")
    explanations = []
    
    for boxes, label, method in detection_results:
        if method == "blur":
            print(f"   🔵 Blurring {len(boxes)} {label}(s)...")
            image = blur_boxes(image, boxes)
            explanations.extend([f"{label} blurred"] * len(boxes))
            
        
        else:
            is_partial = redaction_opts.get("partial", False)
            mode_str = "Partially" if is_partial else "Fully"
            print(f"   ✅ {mode_str} redacting {len(boxes)} {label}(s)...")
            image = redact_boxes(image, boxes, partial=is_partial)
            explanations.extend([f"{label} redacted"] * len(boxes))
    
    if redaction_opts.get("watermark", True):
        print(f"\n📋 Step 7: Adding watermark...")
        image = add_watermark(image, "REDACTED BY OBSCURA - NOT FOR OFFICIAL VERIFICATION")
    
    print(f"\n📋 Step 8: Saving redacted image...")
    print(f"   Saving to: {output_path}")
    success = cv2.imwrite(output_path, image)
    
    if success and os.path.exists(output_path):
        output_size = os.path.getsize(output_path)
        print(f"✅ Redacted image saved successfully ({output_size} bytes)")
    else:
        print(f"❌ ERROR: Failed to save output file!")
        raise ValueError("Failed to save redacted image")
    
    print(f"\n📋 Step 9: Cleanup...")
    if os.path.exists(clean_path):
        os.remove(clean_path)
        print(f"✅ Cleaned up temporary file: {clean_path}")
    
    print(f"\n{'='*70}")
    print(f"✅ REDACTION COMPLETE - {len(explanations)} items redacted")
    print(f"{'='*70}\n")
    
    # Generate the AI summary before returning
    ai_summary = generate_redaction_summary(ocr_results, detection_results, custom_prompt)
    print(f"\n💬 AI Summary Generated: {ai_summary[:50]}...")
    
    return explanations, ai_summary


@app.route("/upload", methods=["POST"])
def upload():
    """
    Main upload endpoint for sensitive data redaction.
    """
    try:
        print(f"\n{'#'*70}")
        print(f"📤 NEW UPLOAD REQUEST RECEIVED")
        print(f"{'#'*70}")
        
        if "image" not in request.files:
            print(f"❌ ERROR: No 'image' key in request.files")
            return jsonify({"error": "Form-data key must be 'image'"}), 400
        
        file = request.files["image"]
        if not file.filename:
            print(f"❌ ERROR: Empty filename")
            return jsonify({"error": "Empty filename"}), 400
        
        options_json = request.form.get("options", "{}")
        try:
            options = json.loads(options_json)
            print(f"⚙️  Redaction options: {options}")
        except json.JSONDecodeError:
            print(f"⚠️  Invalid JSON in options, using defaults")
            options = {}
            
        custom_prompt = request.form.get("custom_prompt", "")
        if custom_prompt:
            print(f"📝 Custom prompt received: {custom_prompt}")
        
        filename = secure_filename(file.filename.lower())
        uid = uuid.uuid4().hex
        name, ext = os.path.splitext(filename)
        saved_name = f"{name}_{uid}{ext}"
        
        original_path = os.path.join(UPLOAD_ORIGINAL, saved_name)
        file.save(original_path)
        print(f"📥 File saved: {filename} → {saved_name}")
        
        file_type, _ = mimetypes.guess_type(original_path)
        if not file_type:
            print(f"❌ ERROR: Unsupported file type")
            return jsonify({"error": "Unsupported file type"}), 400
        
        print(f"📄 File type: {file_type}")
        
        explanations = []
        
        if file_type.startswith("image"):
            print(f"\n🖼️  Processing as IMAGE...")
            output_path = os.path.join(UPLOAD_REDACTED, f"{name}_{uid}_redacted.png")
            
            explanations, ai_summary = process_image_with_options(
                original_path, output_path, options, custom_prompt, source_type="image"
            )
            
            with open(output_path, "rb") as f:
                encoded = base64.b64encode(f.read()).decode()
            
            risk_score = min(len(explanations) * 20, 100)
            
            print(f"\n✅ IMAGE PROCESSING COMPLETE")
            print(f"   Risk score: {risk_score}")
            print(f"   Explanations: {len(explanations)}")
            
            return jsonify({
                "type": "image",
                "risk_score": risk_score,
                "explanations": explanations,
                "redacted_image": encoded,
                "ai_summary": ai_summary
            })
        
        elif file_type == "application/pdf":
            print(f"\n📄 Processing as PDF...")
            temp_dir = os.path.join(UPLOAD_TEMP, uid)
            os.makedirs(temp_dir, exist_ok=True)
            
            try:
                pages = pdf_to_images(original_path, temp_dir)
                print(f"📑 PDF converted to {len(pages)} page(s)")
                
                redacted_pages = []
                for i, page in enumerate(pages, 1):
                    print(f"\n{'─'*70}")
                    print(f"📄 Processing page {i}/{len(pages)}")
                    print(f"{'─'*70}")
                    
                    out_page = page.replace(".png", "_redacted.png")
                    
                    page_explanations, page_ai_summary = process_image_with_options(
                        page, out_page, options, custom_prompt, source_type=f"pdf page {i}"
                    )
                    
                    # For multi-page PDFs, we might just keep the summary of the last page, or concatenate
                    ai_summary = page_ai_summary
                    
                    explanations.extend(page_explanations)
                    redacted_pages.append(out_page)
                
                final_pdf = os.path.join(UPLOAD_REDACTED, f"redacted_{uid}.pdf")
                print(f"\n📄 Creating final PDF: {final_pdf}")
                images_to_pdf(redacted_pages, final_pdf)
                
                if os.path.exists(final_pdf):
                    pdf_size = os.path.getsize(final_pdf)
                    print(f"✅ Final PDF created ({pdf_size} bytes)")
                
                with open(final_pdf, "rb") as f:
                    encoded = base64.b64encode(f.read()).decode()
                
                risk_score = min(len(explanations) * 20, 100)
                
                print(f"\n✅ PDF PROCESSING COMPLETE")
                print(f"   Total pages: {len(pages)}")
                print(f"   Risk score: {risk_score}")
                print(f"   Total redactions: {len(explanations)}")
                
                return jsonify({
                    "type": "pdf",
                    "risk_score": risk_score,
                    "explanations": explanations,
                    "redacted_pdf": encoded,
                    "ai_summary": ai_summary
                })
            
            finally:
                if os.path.exists(temp_dir):
                    shutil.rmtree(temp_dir, ignore_errors=True)
                    print(f"🗑️  Cleaned up temp directory: {temp_dir}")
        
        else:
            print(f"❌ ERROR: Unsupported format: {file_type}")
            return jsonify({"error": "Unsupported format (expected image or PDF)"}), 400
    
    except Exception as e:
        print(f"\n{'!'*70}")
        print(f"❌ EXCEPTION OCCURRED")
        print(f"{'!'*70}")
        traceback.print_exc(file=sys.stderr)
        print(f"{'!'*70}\n")
        return jsonify({"error": str(e)}), 500



@app.route("/metadata", methods=["POST"])
def metadata():
    """
    Extract and analyze metadata from an image.
    """
    if "image" not in request.files:
        return jsonify({"error": "No image provided"}), 400

    file = request.files["image"]
    if file.filename == "":
        return jsonify({"error": "Empty filename"}), 400

    filename = secure_filename(file.filename.lower())
    uid = uuid.uuid4().hex
    name, ext = os.path.splitext(filename)
    original_path = os.path.join(UPLOAD_ORIGINAL, f"{name}_{uid}{ext}")
    file.save(original_path)

    try:
        img = Image.open(original_path)
        exif_data = img._getexif() or {}
        metadata = {}
        
        for tag_id, value in exif_data.items():
            decoded_tag = ExifTags.TAGS.get(tag_id, tag_id)
            
            if decoded_tag == "GPSInfo":
                gps_info = {}
                for gps_tag_id, gps_value in value.items():
                    gps_decoded = ExifTags.GPSTAGS.get(gps_tag_id, gps_tag_id)
                    gps_info[gps_decoded] = str(gps_value)
                metadata["GPSInfo"] = str(gps_info)
            else:
                metadata[decoded_tag] = str(value)

        # Calculate risk based on sensitive tags
        sensitive_tags = ['GPSInfo', 'Make', 'Model', 'DateTime', 'Software', 'Artist', 'Copyright']
        sensitive_count = sum(1 for k in metadata if any(t in str(k) for t in sensitive_tags))
        risk_score = min(sensitive_count * 20, 100)

        explanations = [
            f"{k}: {v[:50]}..." for k, v in metadata.items() 
            if any(t in str(k) for t in sensitive_tags)
        ] or ["No sensitive metadata found"]

        return jsonify({
            "metadata": metadata,
            "risk_score": risk_score,
            "explanations": explanations
        })
        
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": f"Metadata extraction failed: {str(e)}"}), 500


@app.route("/strip-metadata", methods=["POST"])
def strip_metadata():
    """
    Strip all metadata from an image.
    """
    if "image" not in request.files:
        return jsonify({"error": "Form-data key must be 'image'"}), 400

    file = request.files["image"]
    if file.filename == "":
        return jsonify({"error": "Empty filename"}), 400
    
    filename = secure_filename(file.filename.lower())
    uid = uuid.uuid4().hex
    name, ext = os.path.splitext(filename)
    original_path = os.path.join(UPLOAD_ORIGINAL, f"{name}_{uid}{ext}")
    file.save(original_path)

    clean_path = os.path.join(UPLOAD_REDACTED, f"{name}_{uid}_clean.png")
    
    try:
        remove_metadata(original_path, clean_path)

        with open(clean_path, "rb") as f:
            encoded = base64.b64encode(f.read()).decode()

        return jsonify({
            "redacted_image": encoded,
            "message": "Metadata stripped successfully"
        })
        
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": f"Metadata stripping failed: {str(e)}"}), 500


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    print("🚀 Starting Integrated Document Redaction Server...")
    print("📁 Upload directories ready:")
    print(f"   - Original: {UPLOAD_ORIGINAL}")
    print(f"   - Redacted: {UPLOAD_REDACTED}")
    print(f"   - Temp: {UPLOAD_TEMP}")
    print("\n🔧 Available endpoints:")
    print("   - POST /upload (Sensitive data redaction)")
    print("   - POST /metadata (Extract metadata)")
    print("   - POST /strip-metadata (Remove metadata)")
    app.run(debug=False, host='0.0.0.0')
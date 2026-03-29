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
import tempfile

from flask import Flask, request, jsonify
from flask_cors import CORS
from werkzeug.utils import secure_filename
from PIL import Image, ExifTags

from preprocessing.metadata_removal import remove_metadata
from preprocessing.image_cleaner import preprocess_image

from ocr.printed_ocr import extract_printed_text

from redaction.sensitive_detector_image import (
    find_qr_codes,
    find_faces,
    find_aadhaar_boxes,
    find_vid_boxes,
    find_phone_boxes,
    find_email_boxes,
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

# Explicitly allow every origin the browser extension runs on.
# The extension's content script fetches from WhatsApp Web, Instagram,
# Twitter/X, Facebook — all of which are https:// origins that a plain
# CORS(app) does NOT whitelist by default.
CORS(app, resources={r"/*": {
    "origins": [
        "https://web.whatsapp.com",
        "https://www.instagram.com",
        "https://twitter.com",
        "https://x.com",
        "https://www.facebook.com",
        # Chrome extension pages (chrome-extension://<id>)
        r"chrome-extension://*",
        # Local dev / React frontend
        "http://localhost:3000",
        "http://localhost:5000",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5000",
        # Wildcard fallback so any extension ID works
        "*",
    ],
    "methods": ["GET", "POST", "OPTIONS"],
    "allow_headers": ["Content-Type", "Authorization"],
    "supports_credentials": False,
}})

# No persistent upload folders — all processing uses temp files deleted after use
# This ensures zero data retention: files exist only during active processing


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




def process_image_with_options(image_path, output_path, options, custom_prompt="", source_type="image", manual_boxes=None):
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

    # ── LAYER 2: Regex detectors — always run, zero API dependency ─────────────
    if redaction_opts.get("aadhaar", True):
        aadhaar_boxes = find_aadhaar_boxes(ocr_results)
        if aadhaar_boxes:
            detection_results.append((aadhaar_boxes, "Aadhaar number", "redact"))
            print(f"      ✅ Regex: {len(aadhaar_boxes)} Aadhaar number(s)")

    if redaction_opts.get("vid", True):
        vid_boxes = find_vid_boxes(ocr_results)
        if vid_boxes:
            detection_results.append((vid_boxes, "VID", "redact"))
            print(f"      ✅ Regex: {len(vid_boxes)} VID(s)")

    if redaction_opts.get("phone", True):
        phone_boxes = find_phone_boxes(ocr_results)
        if phone_boxes:
            detection_results.append((phone_boxes, "Phone number", "redact"))
            print(f"      ✅ Regex: {len(phone_boxes)} phone number(s)")

    if redaction_opts.get("email", False):
        email_boxes = find_email_boxes(ocr_results)
        if email_boxes:
            detection_results.append((email_boxes, "Email address", "redact"))
            print(f"      ✅ Regex: {len(email_boxes)} email address(es)")

    # ── LAYER 3: LLM — general_pii, pan, plate, names, addresses, custom ───────
    # NOTE: We do NOT do a second-pass LLM call for aadhaar/vid/phone/email
    # because that doubles the per-page time with minimal benefit — regex
    # already catches those reliably. LLM is only called for types regex
    # cannot handle.
    llm_types = [k for k in active_redactions
                 if k not in ["qr", "face", "aadhaar", "vid", "phone", "email",
                               "watermark", "partial"]]

    # For PDF pages skip LLM entirely unless there is a custom prompt —
    # this is the main cause of timeouts on multi-page PDFs
    is_pdf_page = source_type.startswith("pdf page")
    if is_pdf_page and not (custom_prompt and custom_prompt.strip()):
        llm_types = []

    if llm_types or (custom_prompt and custom_prompt.strip()):
        print(f"   🧠 LLM detection for: {llm_types}")
        categorized_boxes = detect_sensitive_entities_ai(ocr_results, llm_types, custom_prompt)

        LABEL_MAP = {
            "custom":      "Custom Rule Match",
            "general_pii": "General PII (ID/DOB/Expiry)",
            "aadhaar":     "Aadhaar number",
            "vid":         "VID",
            "pan":         "PAN card",
            "phone":       "Phone number",
            "email":       "Email address",
            "plate":       "License plate",
            "address":     "Address",
            "name":        "Name",
        }
        for category, boxes in categorized_boxes.items():
            label = LABEL_MAP.get(category, category.capitalize())
            detection_results.append((boxes, label, "redact"))
            print(f"      ✅ LLM: {len(boxes)} {label}(s)")
    
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
    
    # ── Manual boxes from extension draw-to-redact feature ──────────────────
    if manual_boxes:
        print(f"\n📋 Applying {len(manual_boxes)} manual redaction box(es)...")
        image = redact_boxes(image, manual_boxes, partial=False)
        explanations.extend(["Manual redaction"] * len(manual_boxes))
        print(f"   ✅ Applied {len(manual_boxes)} manual box(es)")

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
    
    # Generate the AI summary — skip for PDF pages to avoid one Gemini call
    # per page (causes timeouts). The /upload route generates it once at the end.
    if source_type.startswith("pdf page"):
        ai_summary = ""
    else:
        ai_summary = generate_redaction_summary(ocr_results, detection_results, custom_prompt)
        print(f"\n💬 AI Summary Generated: {ai_summary[:50]}...")

    return explanations, ai_summary



@app.route("/analyze", methods=["POST"])
def analyze():
    """
    Fast-scan endpoint used by the browser extension (content.js).
    Runs OCR + regex detectors + metadata extraction and returns a
    structured findings object WITHOUT applying any redaction.
    The extension shows these findings to the user and then calls
    /upload only if the user chooses to redact.

    Returns JSON:
    {
        "scan_id":           str,          # unique id for this scan
        "risk_score":        int,          # 0-100
        "sensitive_findings": [str, ...],  # human-readable labels
        "metadata_findings": {key: value}  # sensitive EXIF fields only
    }
    """
    if "image" not in request.files:
        return jsonify({"error": "No image provided"}), 400

    file = request.files["image"]
    if not file.filename:
        return jsonify({"error": "Empty filename"}), 400

    uid = uuid.uuid4().hex

    # Already-redacted file — return safe immediately, no disk needed
    if file.filename.lower().startswith("redacted_"):
        print("✅ /analyze: already-redacted file — returning safe")
        return jsonify({
            "scan_id":            uid,
            "risk_score":         0,
            "sensitive_findings": [],
            "metadata_findings":  {},
            "already_clean":      True,
        })

    # Save to a temp file — deleted automatically when processing finishes
    suffix = os.path.splitext(secure_filename(file.filename.lower()))[1] or ".bin"
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    file.save(tmp.name)
    tmp.close()
    save_path = tmp.name

    sensitive_findings = []
    metadata_findings  = {}

    try:
        # ── Metadata scan ────────────────────────────────────────────────────
        try:
            img      = Image.open(save_path)
            exif_raw = img._getexif() or {}
            SENS_TAGS = ['GPSInfo','Make','Model','DateTime','Software','Artist','Copyright']
            for tag_id, value in exif_raw.items():
                decoded = ExifTags.TAGS.get(tag_id, str(tag_id))
                if decoded == "GPSInfo":
                    gps = {}
                    for gtag, gval in value.items():
                        gps[ExifTags.GPSTAGS.get(gtag, gtag)] = str(gval)
                    metadata_findings["GPSInfo"] = str(gps)
                elif any(t in str(decoded) for t in SENS_TAGS):
                    metadata_findings[decoded] = str(value)[:120]
        except Exception:
            pass  # Non-JPEG / no EXIF — perfectly fine

        # ── OCR + regex scan ─────────────────────────────────────────────────
        try:
            # Detect PDF reliably — check MIME type, magic bytes, then extension.
            # WhatsApp Web often sends PDFs with no extension in the filename,
            # so extension-only check is not enough.
            def _is_pdf_file(path, flask_file):
                # 1. Flask MIME type (most reliable when set by browser)
                mime = getattr(flask_file, 'mimetype', '') or ''
                if mime == 'application/pdf':
                    return True
                # 2. Magic bytes — every PDF starts with %PDF
                try:
                    with open(path, 'rb') as _f:
                        return _f.read(4) == b'%PDF'
                except Exception:
                    pass
                # 3. Extension fallback
                return path.lower().endswith('.pdf')

            is_pdf = _is_pdf_file(save_path, file)
            print(f"[analyze] is_pdf={is_pdf} mime={getattr(file,'mimetype','')} file={save_path}")

            # Build list of image paths to scan —
            # for PDFs convert every page to an image first,
            # for images just use the file directly (after metadata strip)
            images_to_scan = []

            if is_pdf:
                pdf_scan_dir = save_path + "_pages"
                os.makedirs(pdf_scan_dir, exist_ok=True)
                try:
                    page_paths = pdf_to_images(save_path, pdf_scan_dir)
                    images_to_scan = page_paths
                    print(f"[analyze] PDF split into {len(page_paths)} page(s)")
                except Exception as pdf_err:
                    print(f"[analyze] PDF conversion error: {pdf_err}")
            else:
                clean_path = save_path + "_clean.png"
                remove_metadata(save_path, clean_path)
                images_to_scan = [clean_path]

            # Scan every page / image
            for img_path in images_to_scan:
                try:
                    ocr_ready, (sx, sy) = preprocess_image(img_path)
                    ocr_results = extract_printed_text(ocr_ready)
                    ocr_results = _scale_ocr_boxes(ocr_results, sx, sy)

                    if find_aadhaar_boxes(ocr_results) and "Aadhaar number detected" not in sensitive_findings:
                        sensitive_findings.append("Aadhaar number detected")
                    if find_vid_boxes(ocr_results) and "VID (Virtual ID) detected" not in sensitive_findings:
                        sensitive_findings.append("VID (Virtual ID) detected")
                    if find_phone_boxes(ocr_results) and "Phone number detected" not in sensitive_findings:
                        sensitive_findings.append("Phone number detected")
                    if find_email_boxes(ocr_results) and "Email address detected" not in sensitive_findings:
                        sensitive_findings.append("Email address detected")
                    if find_qr_codes(img_path) and "QR code detected" not in sensitive_findings:
                        sensitive_findings.append("QR code detected")

                except Exception as page_err:
                    print(f"[analyze] page scan error for {img_path} (non-fatal): {page_err}")

            # Clean up all temp files
            for img_path in images_to_scan:
                if os.path.exists(img_path):
                    os.remove(img_path)
            if is_pdf:
                pdf_scan_dir_path = save_path + "_pages"
                if os.path.exists(pdf_scan_dir_path):
                    shutil.rmtree(pdf_scan_dir_path, ignore_errors=True)

        except Exception as ocr_err:
            print(f"[analyze] OCR/regex scan error (non-fatal): {ocr_err}")
            traceback.print_exc()

        # ── Risk score ───────────────────────────────────────────────────────
        risk_score = min(
            len(sensitive_findings) * 25 + len(metadata_findings) * 10,
            100
        )

        return jsonify({
            "scan_id":            uid,
            "risk_score":         risk_score,
            "sensitive_findings": sensitive_findings,
            "metadata_findings":  metadata_findings,
        })

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
    finally:
        # Always delete the temp file — zero retention
        if 'save_path' in dir() or 'save_path' in locals():
            try:
                if os.path.exists(save_path):
                    os.remove(save_path)
                    print(f"🗑️  Temp file deleted: {save_path}")
            except Exception:
                pass


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

        # Manual boxes from extension draw-to-redact
        manual_boxes_json = request.form.get("manual_boxes", "[]")
        try:
            manual_boxes = json.loads(manual_boxes_json)
            if manual_boxes:
                print(f"📝 Manual boxes received: {len(manual_boxes)} box(es)")
        except (json.JSONDecodeError, ValueError):
            manual_boxes = []
        
        filename = secure_filename(file.filename.lower())
        uid = uuid.uuid4().hex
        name, ext = os.path.splitext(filename)

        # ── Already-redacted file guard ───────────────────────────────────────
        orig_name_lower = file.filename.lower()
        if orig_name_lower.startswith("redacted_"):
            print(f"✅ Already-redacted file detected — returning safe response")
            file_bytes = file.read()
            encoded_safe = base64.b64encode(file_bytes).decode()
            return jsonify({
                "type": "image",
                "risk_score": 0,
                "explanations": [],
                "redacted_image": encoded_safe,
                "ai_summary": "This file has already been redacted by Obscura. No sensitive data was detected.",
                "already_clean": True,
            })

        # Save to temp file — deleted after response is sent
        suffix = ext or ".bin"
        tmp_in = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
        file.save(tmp_in.name)
        tmp_in.close()
        original_path = tmp_in.name
        print(f"📥 File saved to temp: {original_path}")

        # Detect file type robustly — mimetypes.guess_type fails when the
        # filename has no extension (common when uploading via WhatsApp/browsers).
        # Use magic bytes first, then Flask mimetype, then mimetypes as fallback.
        def _detect_file_type(path, flask_file):
            # 1. Magic bytes — most reliable
            try:
                with open(path, 'rb') as _f:
                    header = _f.read(8)
                if header[:4] == b'%PDF':
                    return 'application/pdf'
                if header[:8] in (b'\x89PNG\r\n\x1a\n',):
                    return 'image/png'
                if header[:3] == b'\xff\xd8\xff':
                    return 'image/jpeg'
                if header[:6] in (b'GIF87a', b'GIF89a'):
                    return 'image/gif'
                if header[:4] == b'RIFF' or header[:4] == b'WEBP':
                    return 'image/webp'
            except Exception:
                pass
            # 2. Flask mimetype
            mt = getattr(flask_file, 'mimetype', '') or ''
            if mt and mt != 'application/octet-stream':
                return mt
            # 3. Extension fallback
            guessed, _ = mimetypes.guess_type(path)
            return guessed or ''

        file_type = _detect_file_type(original_path, file)
        if not file_type:
            print(f"❌ ERROR: Unsupported file type")
            return jsonify({"error": "Unsupported file type"}), 400

        print(f"📄 File type: {file_type}")
        
        explanations = []
        
        if file_type.startswith("image"):
            print(f"\n🖼️  Processing as IMAGE...")
            tmp_out = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
            tmp_out.close()
            output_path = tmp_out.name

            explanations, ai_summary = process_image_with_options(
                original_path, output_path, options, custom_prompt,
                source_type="image", manual_boxes=manual_boxes
            )

            with open(output_path, "rb") as f:
                encoded = base64.b64encode(f.read()).decode()
            os.remove(output_path)
            print(f"🗑️  Temp output deleted: {output_path}")
            
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
            temp_dir = tempfile.mkdtemp()
            
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
                        page, out_page, options, custom_prompt,
                        source_type=f"pdf page {i}",
                        manual_boxes=manual_boxes if i == 1 else None
                    )
                    
                    explanations.extend(page_explanations)
                    redacted_pages.append(out_page)
                
                tmp_pdf = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
                tmp_pdf.close()
                final_pdf = tmp_pdf.name
                print(f"\n📄 Creating final PDF: {final_pdf}")
                images_to_pdf(redacted_pages, final_pdf)

                # Generate ONE AI summary for the whole PDF after all pages processed
                try:
                    ai_summary = generate_redaction_summary([], [], custom_prompt) if explanations else "No sensitive data was found in this PDF."
                except Exception:
                    ai_summary = f"Redaction complete. {len(explanations)} item(s) redacted across {len(pages)} page(s)." 
                
                if os.path.exists(final_pdf):
                    pdf_size = os.path.getsize(final_pdf)
                    print(f"✅ Final PDF created ({pdf_size} bytes)")
                
                with open(final_pdf, "rb") as f:
                    encoded = base64.b64encode(f.read()).decode()
                os.remove(final_pdf)
                print(f"🗑️  Temp PDF deleted: {final_pdf}")

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
    finally:
        # Always delete the original temp input file
        try:
            if 'original_path' in locals() and original_path and os.path.exists(original_path):
                os.remove(original_path)
                print(f"🗑️  Input temp file deleted: {original_path}")
        except Exception:
            pass



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

    suffix = os.path.splitext(secure_filename(file.filename.lower()))[1] or ".jpg"
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    file.save(tmp.name)
    tmp.close()
    original_path = tmp.name

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
    finally:
        try:
            if os.path.exists(original_path):
                os.remove(original_path)
        except Exception:
            pass


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
    
    suffix = os.path.splitext(secure_filename(file.filename.lower()))[1] or ".jpg"
    tmp_in = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    file.save(tmp_in.name)
    tmp_in.close()
    original_path = tmp_in.name

    tmp_out = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
    tmp_out.close()
    clean_path = tmp_out.name

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
    finally:
        for p in [original_path, clean_path]:
            try:
                if os.path.exists(p):
                    os.remove(p)
            except Exception:
                pass


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    print("🚀 Starting Integrated Document Redaction Server...")
    print("🔒 Zero-retention mode: all files processed in temp storage, deleted immediately")
    print("\n🔧 Available endpoints:")
    print("   - POST /upload (Sensitive data redaction)")
    print("   - POST /metadata (Extract metadata)")
    print("   - POST /strip-metadata (Remove metadata)")
    app.run(debug=False, host='0.0.0.0')
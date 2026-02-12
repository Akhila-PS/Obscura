"""
Sensitive data detection module for document redaction.
FIXED VERSION - Reduced false positives

Changes:
- Removed aggressive fallback phone detection
- Increased confidence thresholds
- Added Aadhaar format validation
- Added date pattern exclusion
- Added context awareness
"""

import re
import cv2
import numpy as np


# ============================================================================
# OCR TEXT CLEANING
# ============================================================================

def clean_ocr_text(text: str) -> str:
    """
    Fix OCR character mistakes and return digits only.
    """
    text = text.replace("O", "0").replace("o", "0")
    text = text.replace("l", "1").replace("I", "1")
    text = text.replace("B", "8").replace("b", "8")
    text = text.replace("S", "5").replace("s", "5")
    text = text.replace("Z", "2").replace("z", "2")

    text = text.strip()

    # Remove spaces and dashes like: 1234 5678-9012
    text = re.sub(r'[\s\-]+', '', text)

    # Keep only digits
    text = re.sub(r'[^0-9]', '', text)

    return text


def clean_ocr_text_alphanumeric(text: str) -> str:
    """
    Fix OCR character mistakes and return alphanumeric only (for PAN, etc).
    """
    text = text.replace("O", "0").replace("o", "0")
    text = text.replace("l", "1").replace("I", "1")
    
    text = text.strip()
    
    # Remove spaces and dashes
    text = re.sub(r'[\s\-]+', '', text)
    
    # Keep only alphanumeric
    text = re.sub(r'[^A-Za-z0-9]', '', text)
    
    return text.upper()


# ============================================================================
# UTILITY FUNCTIONS FOR FALSE POSITIVE REDUCTION
# ============================================================================

def is_likely_date(text: str) -> bool:
    """
    Check if text is likely a date format to avoid false positives.
    """
    text_lower = text.lower()
    
    # Date patterns
    date_patterns = [
        r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}',  # DD/MM/YYYY, DD-MM-YY
        r'\d{4}[/-]\d{1,2}[/-]\d{1,2}',    # YYYY/MM/DD
        r'\d{2}\.\d{2}\.\d{4}',            # DD.MM.YYYY
    ]
    
    for pattern in date_patterns:
        if re.search(pattern, text):
            return True
    
    # Date-related keywords
    date_keywords = ['dob', 'birth', 'date', 'expiry', 'valid', 'issue', 'lock', 'unlock']
    if any(keyword in text_lower for keyword in date_keywords):
        return True
    
    return False


def has_exclusion_context(text: str, context_before: str = "", context_after: str = "") -> bool:
    """
    Check if text has context suggesting it should NOT be redacted.
    """
    combined_context = (context_before + " " + text + " " + context_after).lower()
    
    # Keywords that suggest the number is NOT sensitive
    exclusion_keywords = [
        'enrollment', 'enrolment', 'roll', 'application',
        'reference', 'transaction', 'serial', 'id', 'number', 'no.',
        'date', 'dob', 'birth', 'lock', 'unlock',
        'issue', 'expiry', 'valid', 'year',
        'page', 'section', 'clause', 'form'
    ]
    
    for keyword in exclusion_keywords:
        if keyword in combined_context:
            return True
    
    return False


def is_valid_aadhaar_format(digits: str) -> bool:
    """
    Validate Aadhaar format beyond just 12 digits.
    
    Real Aadhaar properties:
    - 12 digits
    - First digit is NOT 0 or 1
    - Should not be a simple date pattern
    """
    if len(digits) != 12:
        return False
    
    # First digit should be 2-9 (Aadhaar rule)
    if digits[0] in ['0', '1']:
        print(f"      ℹ️  Rejecting {digits} - Aadhaar cannot start with 0 or 1")
        return False
    
    # Reject if looks like date-based (e.g., 010119902024)
    if re.match(r'^[0-3]\d[0-1]\d\d{4}', digits):
        print(f"      ℹ️  Rejecting {digits} - appears to be date-based")
        return False
    
    # Reject if too repetitive (e.g., 222222222222)
    unique_digits = len(set(digits))
    if unique_digits <= 3:
        print(f"      ℹ️  Rejecting {digits} - too repetitive ({unique_digits} unique digits)")
        return False
    
    return True


# ============================================================================
# QR CODE DETECTION
# ============================================================================

def find_qr_codes(image_path):
    """
    Detect QR codes using multiple methods for better coverage.
    """
    img = cv2.imread(image_path)
    if img is None:
        print(f"❌ Could not load image: {image_path}")
        return []

    boxes = []
    
    # Method 1: OpenCV QRCodeDetector
    try:
        detector = cv2.QRCodeDetector()
        data, bbox, _ = detector.detectAndDecode(img)
        
        if bbox is not None and len(bbox) > 0:
            points = bbox[0].astype(int)
            boxes.append(points.tolist())
            print(f"      ✅ QR code detected via OpenCV")
    except Exception as e:
        print(f"      ⚠️  QRCodeDetector failed: {e}")
    
    # Method 2: detectMulti for multiple QR codes
    try:
        detector = cv2.QRCodeDetector()
        retval, decoded_info, points, straight_qrcode = detector.detectAndDecodeMulti(img)
        
        if retval and points is not None:
            for point_set in points:
                if point_set is not None:
                    pts = point_set.astype(int).tolist()
                    if not any(np.array_equal(pts, existing) for existing in boxes):
                        boxes.append(pts)
    except Exception as e:
        pass
    
    # Method 3: Pyzbar fallback
    try:
        from pyzbar import pyzbar
        decoded_objects = pyzbar.decode(img)
        
        for obj in decoded_objects:
            points = obj.polygon
            if len(points) == 4:
                pts = [[p.x, p.y] for p in points]
                if not any(np.array_equal(pts, existing) for existing in boxes):
                    boxes.append(pts)
            else:
                x, y, w, h = obj.rect
                pts = [[x, y], [x+w, y], [x+w, y+h], [x, y+h]]
                if not any(np.array_equal(pts, existing) for existing in boxes):
                    boxes.append(pts)
    except ImportError:
        pass
    except Exception as e:
        pass

    if boxes:
        print(f"✅ QR codes detected: {len(boxes)}")
    else:
        print(f"ℹ️  No QR codes detected")

    return boxes


# ============================================================================
# FACE DETECTION
# ============================================================================

def find_faces(image_path):
    """
    Detect faces with improved parameters.
    """
    img = cv2.imread(image_path)
    if img is None:
        print(f"❌ Could not load image: {image_path}")
        return []

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    cascade_files = [
        'haarcascade_frontalface_default.xml',
        'haarcascade_frontalface_alt.xml',
        'haarcascade_frontalface_alt2.xml'
    ]
    
    all_faces = []
    
    for cascade_file in cascade_files:
        try:
            face_cascade = cv2.CascadeClassifier(
                cv2.data.haarcascades + cascade_file
            )
            
            faces = face_cascade.detectMultiScale(
                gray, 
                scaleFactor=1.1, 
                minNeighbors=4,
                minSize=(20, 20),
                flags=cv2.CASCADE_SCALE_IMAGE
            )
            
            for (x, y, w, h) in faces:
                all_faces.append((x, y, w, h))
        except Exception as e:
            pass
    
    # Remove duplicates
    unique_faces = []
    for face in all_faces:
        is_duplicate = False
        for existing in unique_faces:
            if _boxes_overlap(face, existing, threshold=0.5):
                is_duplicate = True
                break
        if not is_duplicate:
            unique_faces.append(face)
    
    boxes = []
    for (x, y, w, h) in unique_faces:
        boxes.append([
            [x, y],
            [x + w, y],
            [x + w, y + h],
            [x, y + h]
        ])

    if boxes:
        print(f"✅ Faces detected: {len(boxes)}")
    else:
        print(f"ℹ️  No faces detected")

    return boxes


def _boxes_overlap(box1, box2, threshold=0.5):
    """Check if two boxes overlap significantly."""
    x1, y1, w1, h1 = box1
    x2, y2, w2, h2 = box2
    
    x_left = max(x1, x2)
    y_top = max(y1, y2)
    x_right = min(x1 + w1, x2 + w2)
    y_bottom = min(y1 + h1, y2 + h2)
    
    if x_right < x_left or y_bottom < y_top:
        return False
    
    intersection = (x_right - x_left) * (y_bottom - y_top)
    area1 = w1 * h1
    area2 = w2 * h2
    
    iou = intersection / min(area1, area2)
    return iou > threshold


# ============================================================================
# AADHAAR (12 digits) - WITH VALIDATION
# ============================================================================

def find_aadhaar_boxes(ocr_results):
    """
    Detect Aadhaar numbers with format validation.
    FIXED: Higher confidence threshold + format validation
    """
    boxes = []

    for bbox, text, conf in ocr_results:
        if conf < 0.3:  # ← INCREASED from 0.2
            continue

        # Skip if looks like a date
        if is_likely_date(text):
            continue

        cleaned = clean_ocr_text(text)

        # Exact 12 digits with validation
        if re.fullmatch(r"\d{12}", cleaned):
            if is_valid_aadhaar_format(cleaned):
                boxes.append(bbox)
                print(f"      ✅ Valid Aadhaar: {cleaned[:4]}********")

    # If no exact match, try combining consecutive digit sequences
    if not boxes:
        boxes = find_aadhaar_boxes_combined(ocr_results)

    if boxes:
        print(f"✅ Aadhaar detected: {len(boxes)}")
    else:
        print(f"ℹ️  No Aadhaar numbers detected")

    return boxes


def find_aadhaar_boxes_combined(ocr_results):
    """
    Try to find Aadhaar by combining consecutive digit sequences.
    """
    boxes = []
    digit_sequences = []

    for bbox, text, conf in ocr_results:
        if conf < 0.3:  # ← INCREASED from 0.2
            continue

        cleaned = clean_ocr_text(text)
        if cleaned.isdigit() and len(cleaned) >= 3:
            digit_sequences.append((bbox, cleaned))

    # Try combining up to 4 consecutive sequences
    for i in range(len(digit_sequences)):
        combined = ""
        combined_boxes = []

        for j in range(i, min(i + 4, len(digit_sequences))):
            combined += digit_sequences[j][1]
            combined_boxes.append(digit_sequences[j][0])

            if len(combined) == 12:
                # Validate before adding
                if is_valid_aadhaar_format(combined):
                    boxes.extend(combined_boxes)
                break
            elif len(combined) > 12:
                break

    return boxes


# ============================================================================
# VID (16 digits)
# ============================================================================

def find_vid_boxes(ocr_results):
    """
    Detect VID (Virtual ID) - 16 digits.
    FIXED: Higher confidence threshold
    """
    boxes = []

    for bbox, text, conf in ocr_results:
        if conf < 0.3:  # ← INCREASED from 0.2
            continue

        # Skip dates
        if is_likely_date(text):
            continue

        cleaned = clean_ocr_text(text)

        if re.fullmatch(r"\d{16}", cleaned) or re.fullmatch(r"\d{15}|\d{17}", cleaned):
            boxes.append(bbox)

    if boxes:
        print(f"✅ VID detected: {len(boxes)}")
    else:
        print(f"ℹ️  No VID detected")

    return boxes


# ============================================================================
# PAN CARD
# ============================================================================

def find_pan_boxes(ocr_results):
    """
    Detect PAN (Permanent Account Number).
    Format: 5 letters + 4 digits + 1 letter (e.g., ABCDE1234F)
    """
    boxes = []
    pattern = r'^[A-Z]{5}[0-9]{4}[A-Z]{1}$'

    for bbox, text, conf in ocr_results:
        if conf < 0.4:  # ← INCREASED from 0.3
            continue

        cleaned = clean_ocr_text_alphanumeric(text)

        if re.match(pattern, cleaned):
            boxes.append(bbox)

    if boxes:
        print(f"✅ PAN cards detected: {len(boxes)}")
    else:
        print(f"ℹ️  No PAN cards detected")

    return boxes


# ============================================================================
# PHONE (Indian) - FIXED: REMOVED FALLBACK LOGIC
# ============================================================================

def find_phone_boxes(ocr_results):
    """
    Detect Indian phone numbers (10 digits starting with 6-9).
    FIXED: 
    - Higher confidence threshold
    - Removed aggressive fallback
    - Added context checking
    - Added date exclusion
    """
    boxes = []

    # Build context map
    for i, (bbox, text, conf) in enumerate(ocr_results):
        if conf < 0.4:  # ← INCREASED from 0.15! Much stricter
            continue

        # Skip if looks like a date
        if is_likely_date(text):
            print(f"      ℹ️  Skipping date-like text: {text}")
            continue

        # Get context
        context_before = ""
        context_after = ""
        if i > 0:
            context_before = ocr_results[i-1][1]
        if i < len(ocr_results) - 1:
            context_after = ocr_results[i+1][1]

        # Check for exclusion context (enrollment, DOB, etc.)
        if has_exclusion_context(text, context_before, context_after):
            print(f"      ℹ️  Skipping due to context: {text}")
            continue

        cleaned = clean_ocr_text(text)

        # Only strict Indian mobile pattern (6-9 prefix)
        if re.fullmatch(r"[6-9]\d{9}", cleaned):
            boxes.append(bbox)
            print(f"      ✅ Phone: {cleaned[:3]}*******")

    # ❌ REMOVED: The aggressive fallback logic that caught enrollment numbers!
    # No more "any 10 digits" matching!

    if boxes:
        print(f"✅ Phone numbers detected: {len(boxes)}")
    else:
        print(f"ℹ️  No phone numbers detected")

    return boxes


# ============================================================================
# EMAIL
# ============================================================================

def find_email_boxes(ocr_results):
    """
    Detect email addresses.
    FIXED: Higher confidence threshold
    """
    boxes = []
    pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b'

    for bbox, text, conf in ocr_results:
        if conf >= 0.5 and re.search(pattern, text):  # ← INCREASED from 0.3
            boxes.append(bbox)

    if boxes:
        print(f"✅ Emails detected: {len(boxes)}")
    else:
        print(f"ℹ️  No emails detected")

    return boxes


# ============================================================================
# LICENSE PLATE
# ============================================================================

def find_license_plate_boxes(ocr_results):
    """
    Detect Indian license plates.
    """
    boxes = []
    pattern = r'\b[A-Z]{2}\d{2}[A-Z]{1,2}\d{4}\b'

    for bbox, text, conf in ocr_results:
        if conf < 0.4:
            continue

        cleaned = text.replace(" ", "").upper()

        if re.search(pattern, cleaned):
            boxes.append(bbox)

    if boxes:
        print(f"✅ License plates detected: {len(boxes)}")
    else:
        print(f"ℹ️  No license plates detected")

    return boxes


# ============================================================================
# KEYWORDS
# ============================================================================

def find_keyword_boxes(ocr_results, keywords):
    """
    Detect custom keywords in text.
    """
    if not keywords:
        return []

    boxes = []
    keyword_list = [k.strip().lower() for k in keywords.split(',')]

    for bbox, text, conf in ocr_results:
        if conf < 0.2:
            continue

        text_lower = text.lower()

        if any(k in text_lower for k in keyword_list):
            boxes.append(bbox)

    if boxes:
        print(f"✅ Keyword matches: {len(boxes)}")
    else:
        print(f"ℹ️  No keyword matches found")

    return boxes


# ============================================================================
# EMERGENCY FALLBACK
# ============================================================================

def find_all_numbers_emergency(ocr_results):
    """
    Emergency fallback: detect any number sequence >= 4 digits.
    Use when specific detection fails.
    """
    boxes = []

    for bbox, text, conf in ocr_results:
        if conf < 0.1:
            continue

        cleaned = clean_ocr_text(text)

        if len(cleaned) >= 4 and cleaned.isdigit():
            boxes.append(bbox)

    if boxes:
        print(f"⚠️  Emergency fallback - numbers detected: {len(boxes)}")
    else:
        print(f"ℹ️  No numbers detected in emergency fallback")

    return boxes



 

def validate_detections(boxes, image_shape):
    """
    Validate bounding boxes are within image boundaries.
    """
    height, width = image_shape[:2]
    valid_boxes = []
    
    for box in boxes:
        try:
            valid = True
            for point in box:
                x, y = point
                if x < 0 or x > width or y < 0 or y > height:
                    valid = False
                    break
            
            if valid:
                valid_boxes.append(box)
            else:
                print(f"⚠️  Invalid box coordinates detected and removed")
        except Exception as e:
            print(f"⚠️  Error validating box: {e}")
    
    return valid_boxes
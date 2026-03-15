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
    
    # Method 1: WeChatQRCode (Best for dense QR like E-Aadhaar and PDFs)
    try:
        import os
        base_dir = os.path.dirname(os.path.dirname(__file__))
        model_dir = os.path.join(base_dir, "models", "wechat_qrcode")
        
        if os.path.exists(os.path.join(model_dir, "detect.prototxt")):
            wechat = cv2.wechat_qrcode_WeChatQRCode(
                os.path.join(model_dir, "detect.prototxt"),
                os.path.join(model_dir, "detect.caffemodel"),
                os.path.join(model_dir, "sr.prototxt"),
                os.path.join(model_dir, "sr.caffemodel")
            )
            res, points = wechat.detectAndDecode(img)
            if points:
                for point_set in points:
                    pts = point_set.astype(int).tolist()
                    if not any(np.array_equal(pts, existing) for existing in boxes):
                        boxes.append(pts)
                        print(f"      ✅ QR code detected via WeChatQRCode")
    except Exception as e:
        print(f"      ⚠️  WeChatQRCode failed: {e}")
        
    # Method 2: OpenCV QRCodeDetector
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
    
    # Method 4: Pyzbar fallback for standard codes
    try:
        from pyzbar import pyzbar
        
        # Helper to scale and threshold
        def try_pyzbar(image, boxes):
            decoded_objects = pyzbar.decode(image)
            found = False
            for obj in decoded_objects:
                points = obj.polygon
                if len(points) == 4:
                    pts = [[p.x, p.y] for p in points]
                    if not any(np.array_equal(pts, existing) for existing in boxes):
                        boxes.append(pts)
                        found = True
                else:
                    x, y, w, h = obj.rect
                    pts = [[x, y], [x+w, y], [x+w, y+h], [x, y+h]]
                    if not any(np.array_equal(pts, existing) for existing in boxes):
                        boxes.append(pts)
                        found = True
            return found
            
        if not try_pyzbar(img, boxes):
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            if not try_pyzbar(gray, boxes):
                try_pyzbar(cv2.resize(gray, (0,0), fx=0.5, fy=0.5), boxes) # helpful for high-DPI
                
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


# End of file


# ============================================================================
# REGEX-BASED SENSITIVE DATA DETECTORS (from sensitive_detector_image_ULTRA)
# ============================================================================

def find_aadhaar_boxes(ocr_results):
    """
    Detects Aadhaar numbers in multiple formats:
    - 1234 5678 9012 (with spaces)
    - 1234-5678-9012 (with dashes)
    - 123456789012 (no separators)
    - "Aadhaar: 1234 5678 9012"
    - "UID: 123456789012"
    """
    boxes = []
    
    # Multiple patterns to catch variations
    patterns = [
        r'\d{4}[\s-]?\d{4}[\s-]?\d{4}',  # 12 digits with optional spaces/dashes
        r'(?:aadhaar|uid|आधार)[\s:]+\d{4}[\s-]?\d{4}[\s-]?\d{4}',  # With label
    ]
    
    for bbox, text, conf in ocr_results:
        if conf < 0.5:  # Consistent confidence threshold
            continue
            
        clean_text = clean_ocr_text(text)
        
        for pattern in patterns:
            if re.search(pattern, clean_text, re.IGNORECASE):
                # Verify it's actually 12 digits
                digits_only = re.sub(r'[^0-9]', '', clean_text)
                if len(digits_only) == 12:
                    boxes.append(bbox)
                    print(f"✅ AADHAAR DETECTED: '{text}' → '{digits_only}' (confidence: {conf:.2f})")
                    break  # Don't double-count
    
    return boxes


def find_vid_boxes(ocr_results):
    """
    Detects 16-digit VID (Virtual ID) numbers.
    Format: 1234 5678 9012 3456
    """
    boxes = []
    
    for bbox, text, conf in ocr_results:
        if conf < 0.5:
            continue
            
        clean_text = clean_ocr_text(text)
        
        # Remove all non-digits
        digits_only = re.sub(r'[^0-9]', '', clean_text)
        
        # Check if exactly 16 digits
        if len(digits_only) == 16:
            boxes.append(bbox)
            print(f"✅ VID DETECTED: '{text}' → '{digits_only}' (confidence: {conf:.2f})")
    
    return boxes


def find_phone_boxes(ocr_results):
    """
    Detects Indian phone numbers:
    - 9876543210 (10 digits starting with 6-9)
    - +91 9876543210
    - 91-9876543210
    - "Mobile: 9876543210"
    - "Phone: +91-9876543210"
    """
    boxes = []
    
    patterns = [
        r'\+?91[\s-]?[6-9]\d{9}',  # +91 or 91 prefix
        r'(?:mobile|phone|contact|call|tel)[\s:]+[6-9]\d{9}',  # With label
        r'\b[6-9]\d{9}\b',  # Just 10 digits (word boundary prevents partial matches)
    ]
    
    for bbox, text, conf in ocr_results:
        if conf < 0.5:
            continue
            
        clean_text = clean_ocr_text(text)
        
        for pattern in patterns:
            if re.search(pattern, clean_text, re.IGNORECASE):
                # Verify it's a valid Indian mobile
                digits_only = re.sub(r'[^0-9]', '', clean_text)
                
                # Remove country code if present
                if digits_only.startswith('91') and len(digits_only) == 12:
                    digits_only = digits_only[2:]
                
                if len(digits_only) == 10 and digits_only[0] in '6789':
                    boxes.append(bbox)
                    print(f"✅ PHONE DETECTED: '{text}' → '{digits_only}' (confidence: {conf:.2f})")
                    break
    
    return boxes


def find_email_boxes(ocr_results):
    """
    Bonus: Detect email addresses.
    Format: user@example.com
    """
    boxes = []
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    
    for bbox, text, conf in ocr_results:
        if conf < 0.5:
            continue
            
        if re.search(email_pattern, text):
            boxes.append(bbox)
            print(f"✅ EMAIL DETECTED: '{text}' (confidence: {conf:.2f})")
    
    return boxes
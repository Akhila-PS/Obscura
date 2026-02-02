# redaction/sensitive_detector_image.py
import re

def clean_ocr_text(text: str) -> str:
    """Clean OCR text - fix common OCR mistakes while preserving spaces."""
    # Fix common OCR character confusions
    text = text.replace("O", "0").replace("o", "0")
    text = text.replace("l", "1").replace("I", "1")
    text = text.strip()
    return text


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
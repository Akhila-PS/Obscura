# redaction/sensitive_detector_image.py
import re

def clean_ocr_text(text: str) -> str:
    """Clean OCR text by fixing common OCR mistakes and removing unwanted characters."""
    # Fix common OCR mistakes
    text = text.replace("O", "0").replace("o", "0")
    text = text.replace("l", "1").replace("I", "1")
    text = text.strip()
    # Remove spaces and dashes for digit matching
    text = re.sub(r'[\s\-]+', '', text)
    # Keep only digits for number matching
    text = re.sub(r'[^0-9]', '', text)
    return text


def find_aadhaar_boxes(ocr_results):
    """
    Find Aadhaar numbers (12 digits).
    LOWERED THRESHOLD: 0.2 (was 0.6) to catch large text with low confidence.
    """
    boxes = []
    for bbox, text, conf in ocr_results:
        # CRITICAL: Lower threshold for large text
        if conf < 0.2:  # Changed from 0.6
            continue
            
        cleaned = clean_ocr_text(text)
        
        # Exact 12 digits
        if re.fullmatch(r"\d{12}", cleaned):
            boxes.append(bbox)
            print(f"✅ AADHAAR DETECTED: '{text}' → '{cleaned}' (conf: {conf:.2f})")
        # Also catch 11 or 13 digits (OCR errors)
        elif re.fullmatch(r"\d{11}|\d{13}", cleaned):
            boxes.append(bbox)
            print(f"⚠️  NEAR-AADHAAR: '{text}' → '{cleaned}' ({len(cleaned)} digits, conf: {conf:.2f})")
    
    return boxes


def find_vid_boxes(ocr_results):
    """
    Find VID numbers (16 digits).
    LOWERED THRESHOLD: 0.2 to catch all instances.
    """
    boxes = []
    for bbox, text, conf in ocr_results:
        if conf < 0.2:  # Changed from 0.6
            continue
            
        cleaned = clean_ocr_text(text)
        
        # Exact 16 digits
        if re.fullmatch(r"\d{16}", cleaned):
            boxes.append(bbox)
            print(f"✅ VID DETECTED: '{text}' → '{cleaned}' (conf: {conf:.2f})")
        # Also catch 15 or 17 digits (OCR errors)
        elif re.fullmatch(r"\d{15}|\d{17}", cleaned):
            boxes.append(bbox)
            print(f"⚠️  NEAR-VID: '{text}' → '{cleaned}' ({len(cleaned)} digits, conf: {conf:.2f})")
    
    return boxes


def find_phone_boxes(ocr_results):
    """
    Find Indian phone numbers (10 digits starting with 6-9).
    LOWERED THRESHOLD: 0.15 for better detection.
    ALSO catches all 10-digit numbers as fallback.
    """
    boxes = []
    found_standard = False
    
    for bbox, text, conf in ocr_results:
        if conf < 0.15:  # Changed from 0.6
            continue
            
        cleaned = clean_ocr_text(text)
        
        # Standard Indian phone (starts with 6-9)
        if re.fullmatch(r"[6-9]\d{9}", cleaned):
            boxes.append(bbox)
            found_standard = True
            print(f"✅ PHONE DETECTED: '{text}' → '{cleaned}' (conf: {conf:.2f})")
    
    # FALLBACK: If no standard phones found, catch ANY 10-digit number
    if not found_standard:
        print("⚠️  No standard phones found, trying fallback (all 10-digit numbers)...")
        for bbox, text, conf in ocr_results:
            if conf < 0.1:  # Even lower threshold for fallback
                continue
            cleaned = clean_ocr_text(text)
            if re.fullmatch(r"\d{10}", cleaned):
                boxes.append(bbox)
                print(f"🔥 10-DIGIT NUMBER: '{text}' → '{cleaned}' (conf: {conf:.2f})")
    
    return boxes


def find_aadhaar_boxes_combined(ocr_results):
    """
    Combine adjacent digit sequences to catch split Aadhaar numbers.
    Example: "4269" + "8501" + "9015" → "426985019015"
    """
    boxes = []
    digit_sequences = []
    
    # Collect all digit sequences with their positions
    for bbox, text, conf in ocr_results:
        if conf < 0.2:
            continue
        cleaned = clean_ocr_text(text)
        if cleaned and cleaned.isdigit():
            digit_sequences.append((bbox, cleaned, conf))
    
    # Try to combine sequences that total 12 digits
    for i in range(len(digit_sequences)):
        combined = ""
        combined_boxes = []
        
        for j in range(i, min(i + 4, len(digit_sequences))):  # Try up to 4 sequences
            combined += digit_sequences[j][1]
            combined_boxes.append(digit_sequences[j][0])
            
            if len(combined) == 12:
                # Found a 12-digit combination!
                boxes.extend(combined_boxes)
                print(f"✅ COMBINED AADHAAR: '{combined}' from {len(combined_boxes)} boxes")
                break
            elif len(combined) > 12:
                break
    
    return boxes


def find_all_numbers_emergency(ocr_results):
    """
    NUCLEAR OPTION: Redact ALL number sequences of 4+ digits.
    Use this only if regular detection fails completely.
    """
    boxes = []
    for bbox, text, conf in ocr_results:
        if conf < 0.1:
            continue
        cleaned = clean_ocr_text(text)
        # Any sequence with 4+ digits
        if len(cleaned) >= 4 and cleaned.isdigit():
            boxes.append(bbox)
            print(f"⚠️  NUMBER DETECTED: '{text}' → '{cleaned}' ({len(cleaned)} digits)")
    return boxes


def find_keyword_boxes(ocr_results, keywords):
    """
    Find and redact custom keywords/phrases.
    Keywords should be comma-separated string: "john doe,confidential,secret"
    """
    if not keywords:
        return []
    
    boxes = []
    keyword_list = [k.strip().lower() for k in keywords.split(',')]
    
    for bbox, text, conf in ocr_results:
        if conf < 0.2:
            continue
        
        text_lower = text.lower().strip()
        
        for keyword in keyword_list:
            if keyword in text_lower:
                boxes.append(bbox)
                print(f"✅ KEYWORD MATCH: '{text}' contains '{keyword}' (conf: {conf:.2f})")
                break  # Don't double-count same box
    
    return boxes
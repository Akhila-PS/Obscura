

# test_detection.py
# Run this to see EXACTLY what OCR is reading from your image

import cv2
import easyocr
import re
import sys

def clean_ocr_text(text: str) -> str:
    """Clean OCR text - fix common OCR mistakes."""
    text = text.replace("O", "0").replace("o", "0")
    text = text.replace("l", "1").replace("I", "1")
    text = text.replace("S", "5").replace("s", "5")
    text = text.replace("Z", "2").replace("z", "2")
    text = text.strip()
    return text

# Initialize OCR
print("🔧 Initializing EasyOCR (this takes a moment)...")
reader = easyocr.Reader(['en', 'hi'], gpu=False)

# Get image path from command line
if len(sys.argv) < 2:
    print("❌ Usage: python test_detection.py <image_path>")
    print("   Example: python test_detection.py test_image.png")
    sys.exit(1)

image_path = sys.argv[1]
print(f"\n📷 Loading image: {image_path}")

# Load image
img = cv2.imread(image_path)
if img is None:
    print(f"❌ Failed to load image: {image_path}")
    sys.exit(1)

print(f"✅ Image loaded: {img.shape[1]}x{img.shape[0]} pixels")

# Run OCR
print("\n🔍 Running OCR (this may take a minute)...")
results = reader.readtext(img, paragraph=False, detail=1)

print(f"\n📊 OCR found {len(results)} text elements")
print("="*80)

# Show ALL results
print("\n📝 ALL OCR RESULTS (with confidence scores):")
print("-"*80)
for i, (bbox, text, conf) in enumerate(results, 1):
    clean = clean_ocr_text(text)
    digits_only = re.sub(r'[^0-9]', '', clean)
    
    print(f"{i:3d}. [{conf:.3f}] '{text}'")
    if clean != text:
        print(f"     Cleaned: '{clean}'")
    if digits_only and len(digits_only) >= 4:
        print(f"     Digits: '{digits_only}' ({len(digits_only)} digits)")
    print()

# Check for Aadhaar patterns
print("\n" + "="*80)
print("🔍 CHECKING FOR AADHAAR PATTERNS:")
print("-"*80)

aadhaar_found = False
for i, (bbox, text, conf) in enumerate(results, 1):
    clean = clean_ocr_text(text)
    digits_only = re.sub(r'[^0-9]', '', clean)
    
    # Check different lengths
    if len(digits_only) == 12:
        print(f"✅ EXACT AADHAAR (12 digits): '{text}' → '{digits_only}' (conf: {conf:.3f})")
        aadhaar_found = True
    elif len(digits_only) in [11, 13]:
        print(f"⚠️  NEAR-AADHAAR ({len(digits_only)} digits): '{text}' → '{digits_only}' (conf: {conf:.3f})")
    elif len(digits_only) == 4:
        print(f"🔹 4-DIGIT GROUP: '{text}' → '{digits_only}' (conf: {conf:.3f}) [might be part of Aadhaar]")

if not aadhaar_found:
    print("\n❌ No complete 12-digit Aadhaar found")
    print("\n💡 POSSIBLE REASONS:")
    print("   1. Aadhaar might be split across multiple boxes (see 4-digit groups above)")
    print("   2. OCR might be reading it incorrectly")
    print("   3. Image quality might be too low")
    print("   4. Text might be too small or too large")

# Check for phone numbers
print("\n" + "="*80)
print("🔍 CHECKING FOR PHONE NUMBERS:")
print("-"*80)

phone_found = False
for i, (bbox, text, conf) in enumerate(results, 1):
    clean = clean_ocr_text(text)
    digits_only = re.sub(r'[^0-9]', '', clean)
    
    # Remove country code if present
    if digits_only.startswith('91') and len(digits_only) == 12:
        digits_only = digits_only[2:]
    
    if len(digits_only) == 10 and digits_only[0] in '6789':
        print(f"✅ PHONE NUMBER: '{text}' → '{digits_only}' (conf: {conf:.3f})")
        phone_found = True

if not phone_found:
    print("❌ No phone numbers found")

# Check for VID
print("\n" + "="*80)
print("🔍 CHECKING FOR VID (16 digits):")
print("-"*80)

vid_found = False
for i, (bbox, text, conf) in enumerate(results, 1):
    clean = clean_ocr_text(text)
    digits_only = re.sub(r'[^0-9]', '', clean)
    
    if len(digits_only) == 16:
        print(f"✅ VID: '{text}' → '{digits_only}' (conf: {conf:.3f})")
        vid_found = True
    elif len(digits_only) in [15, 17]:
        print(f"⚠️  NEAR-VID ({len(digits_only)} digits): '{text}' → '{digits_only}' (conf: {conf:.3f})")

if not vid_found:
    print("❌ No VID found")

# Summary
print("\n" + "="*80)
print("📊 SUMMARY:")
print("-"*80)
print(f"Total OCR elements: {len(results)}")
print(f"Lowest confidence: {min(conf for _, _, conf in results):.3f}")
print(f"Highest confidence: {max(conf for _, _, conf in results):.3f}")
print(f"Average confidence: {sum(conf for _, _, conf in results) / len(results):.3f}")

# Count by confidence range
low_conf = sum(1 for _, _, conf in results if conf < 0.3)
med_conf = sum(1 for _, _, conf in results if 0.3 <= conf < 0.6)
high_conf = sum(1 for _, _, conf in results if conf >= 0.6)

print(f"\nConfidence distribution:")
print(f"  Low (< 0.3):     {low_conf:3d} items")
print(f"  Medium (0.3-0.6): {med_conf:3d} items")
print(f"  High (≥ 0.6):    {high_conf:3d} items")

print("\n" + "="*80)
print("💡 RECOMMENDATIONS:")
print("-"*80)

if low_conf > len(results) * 0.5:
    print("⚠️  More than 50% items have low confidence")
    print("   → Image quality might be poor")
    print("   → Try increasing image resolution")
    print("   → Consider adjusting preprocessing")

if not aadhaar_found:
    # Check if we have 4-digit groups
    four_digit_groups = [text for _, text, _ in results 
                         if len(re.sub(r'[^0-9]', '', clean_ocr_text(text))) == 4]
    if len(four_digit_groups) >= 3:
        print("\n🔍 Found multiple 4-digit groups - Aadhaar might be split!")
        print("   You may need to implement box combining logic")
        print("   See TROUBLESHOOTING_GUIDE.md for 'find_aadhaar_boxes_combined'")

print("\n✅ Diagnostic complete!")
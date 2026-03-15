# ocr/printed_ocr.py

import easyocr

# Initialize EasyOCR with English + Hindi so Indian documents
# (Aadhaar, PAN, voter ID etc.) are read correctly including
# Devanagari labels that bracket the sensitive numbers.
reader = easyocr.Reader(
    ['en', 'hi'],
    gpu=False,
    model_storage_directory='./models',
    download_enabled=True,
    verbose=False
)

def extract_printed_text(image, batch_mode=True):

    print(f"\n📝 Starting OCR text extraction...")

    try:
        results = reader.readtext(
            image,
            batch_size=1,
            workers=0,
            paragraph=False,
            min_size=5,
            # Lowered from 0.5 → 0.3 so digits/numbers printed on coloured
            # ID-card backgrounds (which score lower confidence) are not
            # silently dropped before ever reaching the LLM detector.
            text_threshold=0.3,
            low_text=0.2,
        )

        print(f"✅ OCR completed: {len(results)} text regions found")

        if results:
            print(f"\n📋 Sample OCR results (first 5):")
            for i, (bbox, text, conf) in enumerate(results[:5]):
                print(f"   [{i+1}] Text: '{text}' | Confidence: {conf:.2f}")

            if len(results) > 5:
                print(f"   ... and {len(results) - 5} more text regions")

            avg_conf = sum(conf for _, _, conf in results) / len(results)
            high_conf = sum(1 for _, _, conf in results if conf > 0.7)
            med_conf  = sum(1 for _, _, conf in results if 0.3 <= conf <= 0.7)
            low_conf  = sum(1 for _, _, conf in results if conf < 0.3)

            print(f"\n📊 OCR Confidence Statistics:")
            print(f"   Average: {avg_conf:.2f}")
            print(f"   High (>0.7):       {high_conf} regions")
            print(f"   Medium (0.3-0.7):  {med_conf} regions")
            print(f"   Low (<0.3):        {low_conf} regions")
        else:
            print(f"⚠️  WARNING: No text detected by OCR!")
            print(f"   Possible causes:")
            print(f"   - Image quality too low")
            print(f"   - Text too small or blurry")
            print(f"   - Non-standard fonts")
            print(f"   - Image preprocessing failed")

        return results

    except Exception as e:
        print(f"❌ ERROR during OCR: {e}")
        import traceback
        traceback.print_exc()
        return []
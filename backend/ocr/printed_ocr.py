import easyocr

_reader = None

def _get_reader():
    global _reader
    if _reader is None:
        print("📝 Initialising EasyOCR...")
        _reader = easyocr.Reader(
            ['en', 'hi'],
            gpu=False,
            model_storage_directory='./models',
            download_enabled=True,
            verbose=False
        )
    return _reader

def extract_printed_text(image, batch_mode=True):
    print(f"\n📝 Starting OCR text extraction...")
    try:
        reader = _get_reader()
        results = reader.readtext(
            image, batch_size=1, workers=0,
            paragraph=False, min_size=5,
            text_threshold=0.3, low_text=0.2,
        )
        print(f"✅ OCR completed: {len(results)} text regions found")
        return results
    except Exception as e:
        print(f"❌ ERROR during OCR: {e}")
        import traceback
        traceback.print_exc()
        return []
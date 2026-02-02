# ocr/printed_ocr.py
import easyocr

# Initialize EasyOCR reader once (reused across calls)
reader = easyocr.Reader(['en'], gpu=False)


def extract_printed_text(image):
    """
    Accepts a numpy image (already preprocessed by preprocess_image in main.py).
    
    Args:
        image: Preprocessed numpy array from cv2
        
    Returns:
        List of tuples: [(bbox, text, confidence), ...]
        where bbox is [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
    """
    # Run OCR directly - image is ALREADY preprocessed
    # DO NOT preprocess again here!
    results = reader.readtext(image)
    
    # Filter by confidence AND format bounding boxes
    formatted = []
    for bbox, text, conf in results:
        if conf >= 0.5:  # Consistent confidence threshold
            # Ensure integer coordinates for cv2
            bbox = [[int(x), int(y)] for x, y in bbox]
            formatted.append((bbox, text, conf))
    
    print(f"📊 OCR found {len(results)} items, kept {len(formatted)} after confidence filter")
    
    return formatted
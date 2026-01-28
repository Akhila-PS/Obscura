import easyocr

reader = easyocr.Reader(['en'], gpu=False)

def extract_printed_text(image):
    """
    Accepts a numpy image (from OpenCV preprocessing)
    Returns [(bbox, text, confidence)]
    """
    results = reader.readtext(image)
    formatted = []

    for bbox, text, conf in results:
        bbox = [[int(x), int(y)] for x, y in bbox]
        formatted.append((bbox, text, conf))

    return formatted

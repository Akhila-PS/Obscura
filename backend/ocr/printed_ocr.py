import easyocr

reader = easyocr.Reader(['en'], gpu=False)

def extract_printed_text(image_path):
    return reader.readtext(image_path)

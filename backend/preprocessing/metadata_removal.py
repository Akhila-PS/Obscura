from PIL import Image

def remove_metadata(input_path, output_path):
    img = Image.open(input_path)

    # Force standard RGB (OpenCV safe)
    if img.mode != "RGB":
        img = img.convert("RGB")

    data = list(img.getdata())
    clean = Image.new("RGB", img.size)
    clean.putdata(data)
    clean.save(output_path)

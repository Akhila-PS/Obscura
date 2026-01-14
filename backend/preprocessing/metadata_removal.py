from PIL import Image

def remove_metadata(input_path, output_path):
    img = Image.open(input_path)
    data = list(img.getdata())
    clean = Image.new(img.mode, img.size)
    clean.putdata(data)
    clean.save(output_path)

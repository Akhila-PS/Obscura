from PIL import Image
from pdf2image import convert_from_path
import os

# Convert multiple images to a single PDF
def images_to_pdf(image_paths, output_pdf):
    images = [Image.open(p).convert("RGB") for p in image_paths]
    if images:
        images[0].save(
            output_pdf,
            save_all=True,
            append_images=images[1:]
        )

# Convert PDF to images
def pdf_to_images(pdf_path, output_dir):
    # Make sure output directory exists
    os.makedirs(output_dir, exist_ok=True)

    pages = convert_from_path(pdf_path, dpi=300)
    image_paths = []

    for i, page in enumerate(pages):
        img_path = os.path.join(output_dir, f"page_{i+1}.png")
        page.save(img_path, "PNG")
        image_paths.append(img_path)

    return image_paths

# Example usage:
# images_to_pdf(["img1.png", "img2.png"], "output.pdf")
# pdf_to_images("output.pdf", "output_images")

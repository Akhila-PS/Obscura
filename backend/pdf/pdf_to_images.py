from pdf2image import convert_from_path
import os

def pdf_to_images(pdf_path, output_dir):
    pages = convert_from_path(pdf_path, dpi=300)
    image_paths = []

    for i, page in enumerate(pages):
        img_path = os.path.join(output_dir, f"page_{i}.png")
        page.save(img_path, "PNG")
        image_paths.append(img_path)

    return image_paths

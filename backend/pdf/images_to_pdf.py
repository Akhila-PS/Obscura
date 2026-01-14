from PIL import Image

def images_to_pdf(image_paths, output_pdf):
    images = [Image.open(p).convert("RGB") for p in image_paths]
    images[0].save(
        output_pdf,
        save_all=True,
        append_images=images[1:]
    )

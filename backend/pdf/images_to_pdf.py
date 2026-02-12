# pdf/images_to_pdf.py
from PIL import Image
import os


def images_to_pdf(image_paths, output_pdf):
    """
    Convert multiple images to a single PDF.
    
    
        image_paths: 
        output_pdf: 
        
   
    """
    if not image_paths:
        raise ValueError("No image paths provided")
    
    images = []
    
    # Load all images, skip corrupted ones
    for path in image_paths:
        try:
            img = Image.open(path).convert("RGB")
            images.append(img)
        except Exception as e:
            print(f"⚠️  Failed to load image {path}: {e}")
            continue
    
    if not images:
        raise ValueError("No valid images could be loaded")
    
    # Save as PDF
    try:
        images[0].save(
            output_pdf,
            format="PDF",
            save_all=True,
            append_images=images[1:] if len(images) > 1 else []
        )
        print(f"✅ Created PDF with {len(images)} page(s)")
    except Exception as e:
        raise ValueError(f"Failed to create PDF: {e}") from e
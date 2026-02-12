# pdf/pdf_to_images.py
import os
import shutil
from pdf2image import convert_from_path


def _get_poppler_path():
    
    path = os.environ.get("POPPLER_PATH")
    if path and os.path.isdir(path):
        return path
    
    # Check if pdftoppm is available in system PATH
    if shutil.which("pdftoppm"):
        return None
    
    return None


def pdf_to_images(pdf_path, output_dir):
   
    os.makedirs(output_dir, exist_ok=True)

    poppler_path = _get_poppler_path()
    kwargs = {"dpi": 300}
    
    if poppler_path:
        kwargs["poppler_path"] = poppler_path

    try:
        pages = convert_from_path(pdf_path, **kwargs)
    except Exception as e:
        err = str(e).strip()
        
        if "poppler" in err.lower() or "pdftoppm" in err.lower() or "pdfinfo" in err.lower():
            raise ValueError(
                "❌ Poppler not found. Please install Poppler and add its 'bin' folder to PATH, "
                "or set POPPLER_PATH environment variable to point to the bin folder. "
                "Restart your terminal (and Flask) after changing PATH. "
                f"Original error: {err}"
            ) from e
        
        raise ValueError(f"PDF conversion failed: {err}") from e

    image_paths = []
    for i, page in enumerate(pages, 1):
        img_path = os.path.join(output_dir, f"page_{i}.png")
        page.save(img_path, "PNG")
        image_paths.append(img_path)

    return image_paths
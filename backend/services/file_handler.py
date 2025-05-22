import os
from pdf2image import convert_from_path
from backend.utils.helpers import resize_img
import ocrmypdf
from backend.core.config import settings

# Ensure directories for page images and figures exist
def setup_directories():
    directories = [
        os.path.join(settings.IMG_DIR, "pages"),
        os.path.join(settings.IMG_DIR, "figures")
    ]
    for directory in directories:
        os.makedirs(directory, exist_ok=True)

setup_directories()

def split_pdf(pdf_path: str):
    pages = []
    page_images = convert_from_path(pdf_path, 400)
    pdf_name = os.path.basename(pdf_path).replace('.pdf', '')
    for i, page in enumerate(page_images):
        page = resize_img(page, size=1440)
        page_img_path = os.path.join(settings.IMG_DIR, "pages", f"{pdf_name}_{i}.png")
        page.save(page_img_path, "PNG")
        metadata = {
            "index": i,
            "image": page_img_path,
            "text": "",
            "markdown": "",
        }
        pages.append(metadata)
    return pages

def ocr_pdf_to_pdf(pdf_path, output_dir):
    new_filename = os.path.basename(pdf_path).replace('.pdf', '_ocr.pdf')
    new_pdf_path = os.path.join(output_dir, os.path.basename(new_filename))
    ocrmypdf.ocr(pdf_path, new_pdf_path, use_threads=True, skip_text=True, output_type="pdf")
    return new_pdf_path
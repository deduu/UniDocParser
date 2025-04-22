import os
from pdf2image import convert_from_path
from backend.utils.helpers import resize_img

# Ensure directories for page images and figures exist
def setup_directories():
    directories = [
        os.path.join("backend", "img", "pages"),
        os.path.join("backend", "img", "figures")
    ]
    for directory in directories:
        os.makedirs(directory, exist_ok=True)

setup_directories()

def split_pdf(pdf_path: str):
    pages = []
    page_images = convert_from_path(pdf_path, 400)
    for i, page in enumerate(page_images):
        page = resize_img(page, size=1440)
        page_img_path = os.path.join("backend", "img", "pages", f"page_{i}.png")
        page.save(page_img_path, "PNG")
        metadata = {
            "index": i,
            "file_path": pdf_path,
            "source": os.path.basename(pdf_path),
            "image": page_img_path,
            "text": "",
            "markdown": "",
            "yolo_used": True,
            "yolo_figures": [],
            "elements": [],
        }
        pages.append(metadata)
    return pages

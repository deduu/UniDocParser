import os
from pdf2image import convert_from_path

# Ensure directories for page images and figures exist
def setup_directories():
    directories = [
        os.path.join("backend", "img", "pages"),
        os.path.join("backend", "img", "figures")
    ]
    for directory in directories:
        os.makedirs(directory, exist_ok=True)

setup_directories()

def resize_img(image, width=1440):
    image = image.convert('RGB')
    basewidth = width
    wpercent = (basewidth / float(image.size[0]))
    hsize = int((float(image.size[1]) * float(wpercent)))
    return image.resize((basewidth, hsize))

def split_pdf(pdf_path: str):
    pages = []
    page_images = convert_from_path(pdf_path, 300)
    for i, page in enumerate(page_images):
        page = resize_img(page, width=1440)
        page_img_path = os.path.join("backend", "img", "pages", f"page_{i}.png")
        page.save(page_img_path, "PNG")
        metadata = {
            "index": i,
            "file_path": pdf_path,
            "source": os.path.basename(pdf_path),
            "image": page_img_path,
            "text": "",
            "figures": []
        }
        pages.append(metadata)
    return pages

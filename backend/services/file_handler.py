import os
from pdf2image import convert_from_path
from PIL import Image
from backend.utils.helpers import resize_img
import ocrmypdf
from backend.core.config import settings

def handle_file(file_path: str):
    pages = []

    # Check if the file is a PDF
    if file_path.lower().endswith('.pdf'):
        try:
            page_images = convert_from_path(file_path, 400)
            pdf_name = os.path.basename(file_path).replace('.pdf', '')
            for i, page in enumerate(page_images):
                page = resize_img(page, size=1440)
                page_img_path = os.path.join(settings.IMG_PAGES_DIR, f"{pdf_name}_{i}.png")
                page.save(page_img_path, "PNG")
                metadata = {
                    "index": i,
                    "image_path": page_img_path,
                    "text": "",
                    "markdown": "",
                }
                pages.append(metadata)
        except Exception as e:
            print(f"Error converting PDF to images: {e}")
            return None
    # Check if the file is an image
    elif file_path.lower().endswith(('.png', '.jpg', '.jpeg')):
        try:
            img = Image.open(file_path)
            img = resize_img(img, size=1440)
            img_path = os.path.join(settings.IMG_PAGES_DIR, os.path.basename(file_path))
            # change the file extension to png
            if img_path.lower().endswith(('.jpg', '.jpeg')):
                img_path = img_path.replace('.jpg', '.png').replace('.jpeg', '.png')
            elif img_path.lower().endswith('.png'):
                img_path = img_path.replace('.png', '.png')
            else:
                img_path = os.path.join(settings.IMG_PAGES_DIR, os.path.basename(file_path).replace('.jpg', '.png').replace('.jpeg', '.png'))
            img.save(img_path, "PNG")
            metadata = {
                "index": 0,
                "image_path": img_path,
                "text": "",
                "markdown": "",
                "elements": [],
            }
            pages.append(metadata)
        except Exception as e:
            print(f"Error processing image: {e}")
            return None
    else:
        print("Unsupported file format.")
        return None
    return pages

def ocr_pdf_to_pdf(pdf_path, output_dir):
    new_filename = os.path.basename(pdf_path).replace('.pdf', '_ocr.pdf')
    new_pdf_path = os.path.join(output_dir, os.path.basename(new_filename))
    ocrmypdf.ocr(pdf_path, new_pdf_path, use_threads=True, force_ocr=True, output_type="pdf")
    return new_pdf_path
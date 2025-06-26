import os
from pdf2image import convert_from_path
from PIL import Image
import ocrmypdf
from backend.utils.helpers import resize_img
from backend.core.config import settings

def handle_file(file_path: str):
    pages = []

    # Check if the file is a PDF
    if file_path.lower().endswith('.pdf'):
        try:
            page_images = convert_from_path(file_path, 400)
            pdf_name = os.path.basename(file_path).replace('.pdf', '')
            for i, page in enumerate(page_images):
                page = resize_img(page, size=1920)
                page_img_path = os.path.join(settings.IMG_PAGES_DIR, f"{pdf_name}_{i}.jpeg")
                page.save(page_img_path, "JPEG")
                metadata = {
                    "index": i,
                    "status": "Success",
                    "image": page_img_path,
                    "text": "",
                    "markdown": "",
                    "elements": [],
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
            if img_path.lower().endswith(('.jpg', '.png')):
                img_path = img_path.replace('.jpg', '.jpeg').replace('.png', '.jpeg')
            elif img_path.lower().endswith('.jpeg'):
                img_path = img_path.replace('.jpeg', '.jpeg')
            else:
                img_path = os.path.join(settings.IMG_PAGES_DIR, os.path.basename(file_path).replace('.jpg', '.jpeg').replace('.png', '.jpeg'))
            img.save(img_path, "JPEG")
            metadata = {
                "index": 0,
                "status": "Success",
                "image": img_path,
                "text": "",
                "markdown": "",
                "elements": [],
            }
            pages.append(metadata)
        except Exception as e:
            print(f"Error processing image: {e}")
            return None
    # Check if the file is an excel file
    elif file_path.lower().endswith(('.xls', '.xlsx')):
        # import 
        print(f"excel file is being processed...")
        import openpyxl

        try:
            wb = openpyxl.load_workbook(file_path)
            for i, sheet in enumerate(wb.sheetnames):
                # excel2img.export_img("D:\Test Read Excel\docs\Simple personal cash flow statement.xlsx", f"img/Sheet{i+1}-{sheet}.jpeg", page=sheet)
                # img = Image.open(f"img/Sheet{i+1}-{sheet}.jpeg")
                # img = resize_img(img, size=1440)
                # img.save(f"img/Sheet{i+1}-{sheet}.jpeg")

                metadata = {
                    "index": i,
                    "status": "Success",
                    "image": f"img/Sheet{i+1}-{sheet}.jpeg",
                    "text": "",
                    "markdown": "",
                    "elements": [],
                }
                pages.append(metadata)
        except Exception as e:
            print(f"Error processing Excel file: {e}")
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
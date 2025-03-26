import os
from pdf2image import convert_from_path

# Folder structure setup
DIRECTORIES = ["img/pages", "img/figures"]
for dir in DIRECTORIES:
    os.makedirs(os.path.join(dir), exist_ok=True)

# handle image size
def resize_img(image, width=1440):
    # change the image to RGB mode
    image = image.convert('RGB')

    # change image width and maintain the aspect ratio
    basewidth = width
    wpercent = (basewidth / float(image.size[0]))

    # change the height of the image
    hsize = int((float(image.size[1]) * float(wpercent)))

    # resize the image
    image = image.resize((basewidth, hsize))

    return image

# Function to split PDF into images
def split_pdf(pdf_path, pages):
    page_images = convert_from_path(pdf_path, 300)
    for i, page in enumerate(page_images):
        # Save Image
        page = resize_img(image=page, width=1440)
        path = f"./img/pages/page_{i}.png"
        page.save(path, "PNG")

        # Save Page Metadata
        metadata = {
            "index": i,
            "file_path": pdf_path,
            "source": os.path.basename(pdf_path),
            "image": path,
            "text": "",
            "figures": []
        }
        pages.append(metadata)

    return pages
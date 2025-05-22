from PIL import Image
import re
import io
import base64

# Function to convert a string to lowercase and remove leading/trailing whitespace.
def process_string(string):
    string = string.lower()
    string = string.replace('fig', 'figure')
    string = re.sub(r'[^\w\s]', '', string)
    string = re.sub(r'\s+', ' ', string)
    return string

# handle image size
def resize_img(image, size=1440):
    image = image.convert('RGB')
    width, height = image.size
    greater = max(width, height)
    basesize = size
    percent = (basesize / float(greater))
    hsize = int((float(height) * float(percent)))
    wsize = int((float(width) * float(percent)))
    return image.resize((wsize, hsize))

# Fuction to resize the image to the specified width while maintaining the aspect ratio.
def resize_img_from_path(image_path: str, size=720) -> Image:
    image = Image.open(image_path)
    image = image.convert("RGB")
    width, height = image.size
    greatest = max(width, height)
    smallest = min(width, height)
    if greatest > size:
        image = resize_img(image, size=size)
    elif smallest < 28:
        percent = (28 / float(smallest))
        hsize = int((float(height) * float(percent)))
        wsize = int((float(width) * float(percent)))
        image = image.resize((wsize, hsize))
    pil_image = image.copy()
    return pil_image

# Function to convert an image to base64 string.
def image_to_base64(image_path, quality=50):
    img = Image.open(image_path)
    img = img.convert("RGB")
    buffer = io.BytesIO()
    img.save(buffer, format="JPEG", quality=quality)
    buffer.seek(0)
    compressed_base64 = base64.b64encode(buffer.read()).decode("utf-8")
    return f"data:image/jpeg;base64,{compressed_base64}"
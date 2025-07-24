from PIL import Image, ImageFilter
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
    greatest = max(width, height)
    smallest = min(width, height)
    basesize = size
    if smallest < 28:
        percent = (28 / float(smallest))
        hsize = int((float(height) * float(percent)))
        wsize = int((float(width) * float(percent)))
    elif greatest > basesize:
        percent = (basesize / float(greatest))
        hsize = int((float(height) * float(percent)))
        wsize = int((float(width) * float(percent)))
    else:
        hsize = height
        wsize = width
    image = image.resize((wsize, hsize), Image.Resampling.LANCZOS)
    image = image.filter(ImageFilter.SHARPEN)
    return image

# Function to resize the image to the specified width while maintaining the aspect ratio.
def resize_img_from_path(image_path: str, size=720) -> Image:
    image = Image.open(image_path)
    image = image.convert("RGB")
    image = resize_img(image, size=size)
    return image

# Function to convert an image to base64 string.
def image_to_base64(image_path, quality=50):
    img = Image.open(image_path)
    img = img.convert("RGB")
    buffer = io.BytesIO()
    img.save(buffer, format="JPEG", quality=quality)
    buffer.seek(0)
    compressed_base64 = base64.b64encode(buffer.read()).decode("ascii")
    return f"data:image/jpeg;base64,{compressed_base64}"
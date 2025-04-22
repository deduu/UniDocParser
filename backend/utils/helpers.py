from PIL import Image
import re

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
    wpercent = (basesize / float(greater))
    hsize = int((float(height) * float(wpercent)))
    wsize = int((float(width) * float(wpercent)))
    return image.resize((wsize, hsize))

# Fuction to resize the image to the specified width while maintaining the aspect ratio.
def resize_img_from_path(image_path: str, size=720) -> Image:
    image = Image.open(image_path)
    image = image.convert("RGB")
    width, height = image.size
    greater = max(width, height)
    if greater > size:
        image = resize_img(image, size=size)
    pil_image = image.copy()
    return pil_image
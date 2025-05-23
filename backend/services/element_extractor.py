from unstructured.partition.image import partition_image
import markdownify
import os
from PIL import Image
from backend.utils.helpers import resize_img_from_path, image_to_base64
from backend.core.config import settings

# Function to extract elements from image pages
def element_extractor(image_path):
    image_name = os.path.basename(image_path).replace('.png', '')
    image_filepath = os.path.join(settings.IMG_FIGURES_DIR, f"{image_name}_figures")

    raw_pdf_elements = partition_image(
        filename=image_path,
        extract_images_in_pdf=True,
        extract_image_block_to_payload=False,
        extract_image_block_output_dir=image_filepath,
        infer_table_structure=True,
        languages=["eng", "ind"]
    )
    return raw_pdf_elements

# Function to extract bounding box coordinates from the element.
def extract_bbox(points):
    x_coords = [point[0] for point in points]
    y_coords = [point[1] for point in points]

    return [min(x_coords), min(y_coords), max(x_coords), max(y_coords)]

# Fuction to extract metadata from Unstructured elements
def extract_unstructured_elements(elements, page_num):
    element_metadata = []
    figure_list = []

    # Process elements and figure relationships
    for i, element in enumerate(elements):
        unstructured_element = element.metadata.to_dict()
        element_bbox = extract_bbox(unstructured_element["coordinates"]["points"])
        try:
            element_text = str(element)
        except:
            element_text = ""

        if "unstructured.documents.elements.Image" in str(type(element)):
            image_path = unstructured_element["image_path"]
            
            pil_image = resize_img_from_path(image_path, size=560)
            new_image_path = image_path
            pil_image.save(new_image_path, format="PNG")

            element_metadata.append({
                "idx": i,
                "type": "image",
                "bbox": element_bbox,
                "text": "",
                "image_metadata": {
                    "image_type": "",
                    "caption": "",
                    "description": "",
                    "ocr_string": element_text,
                    "image_base64": image_to_base64(image_path=image_path, quality=20),
                },
            })

            figure_list.append({
                "page_num": page_num,
                "idx": i,
                "image_path": new_image_path,
                "generated_text": ""
            })

        else:
            element_type = "text"

            if "unstructured.documents.elements.Table" in str(type(element)):
                element_type = "table"
                element_text = markdownify.markdownify(element.metadata.text_as_html)

            element_metadata.append({
                "idx": i,
                "type": element_type,
                "bbox": element_bbox,
                "text": element_text,
            })

    return element_metadata, figure_list

# Extract elements from PDF
def extract_elements(pages):
    figure_list = []
    elements = []
    for i, page in enumerate(pages):
        elements.append(element_extractor(image_path=page["image_path"]))
            
    for i, page in enumerate(pages):
        if i < len(elements):
            page["elements"], figures = extract_unstructured_elements(elements=elements[i], page_num=i)
            figure_list += figures
        else:
            # Handle missing elements appropriately
            page["elements"] = []
            print(f"Warning: No elements found for page index {i}")
    return pages, figure_list
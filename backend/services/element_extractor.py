from unstructured.partition.image import partition_image
import markdownify
import os
from PIL.Image import Image
from backend.utils.helpers import resize_img_from_path
import io
import base64

# Function to extract elements from image pages
def element_extractor(image_path, page_num):
    image_filepath = os.path.join(
        "backend", "img", "figures", f"{page_num}"
    )
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

# Function to convert an image to base64 string.
def image_to_base64(image_path, quality=50):
    img = Image.open(image_path)
    img = img.convert("RGB")
    buffer = io.BytesIO()
    img.save(buffer, format="JPEG", quality=quality)
    buffer.seek(0)
    compressed_base64 = base64.b64encode(buffer.read()).decode("utf-8")
    return compressed_base64

# Fuction to extract metadata from Unstructured elements
def extract_elements_to_text(elements, figures):
    element_metadata = []

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
            yolo_idx = None

            # check if the image is in figures
            for j, figure in enumerate(figures):
                fig_bbox = figure["bbox"]
                px_tol = 20
                fig_bbox = [fig_bbox[0]-px_tol, fig_bbox[1]-px_tol, fig_bbox[2]+px_tol, fig_bbox[3]+px_tol]
                if (element_bbox[0] >= fig_bbox[0] and element_bbox[1] >= fig_bbox[1] and
                    element_bbox[2] <= fig_bbox[2] and element_bbox[3] <= fig_bbox[3]):
                    yolo_idx = j
                    break

            # if yolo figure is used skip the image
            if yolo_idx and figures[yolo_idx]["element_index"] != 9999:
                continue
            elif yolo_idx is not None:
                figures[yolo_idx]["element_index"] = i
                element_bbox = fig_bbox
                image_path = figures[yolo_idx]["file_path"]
            
            pil_image = resize_img_from_path(image_path, size=720)

            element_metadata.append({
                "type": "image",
                "bbox": element_bbox,
                "text": "",
                "caption": "",
                "description": "",
                "ocr_string": element_text,
                "image_path": image_path,
                "pil_image": pil_image,
                "image_base64": image_to_base64(image_path=image_path, quality=25),
                "yolo_index": yolo_idx
            })
        else:
            element_type = "text"

            if "unstructured.documents.elements.Table" in str(type(element)):
                element_type = "table"
                element_text = markdownify.markdownify(element.metadata.text_as_html)

            element_metadata.append({
                # "idx": i,
                "type": element_type,
                "bbox": element_bbox,
                "text": element_text,
            })

    return element_metadata

# Extract elements from PDF
def extract_elements(pages):
    elements = []
    for i, page in enumerate(pages):
        image_path = page["image"]
        elements.append(element_extractor(image_path=image_path, page_num=i))
            
    print("Number of pages:", len(pages))
    for i, page in enumerate(pages):
        if i < len(elements):
            page["elements"] = extract_elements_to_text(elements[i], page["figures"])
        else:
            # Handle missing elements appropriately
            page["elements"] = []
            print(f"Warning: No elements found for page index {i}")
    return pages
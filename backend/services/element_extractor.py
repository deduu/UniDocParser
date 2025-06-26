import markdownify
import os
from backend.utils.helpers import resize_img_from_path, image_to_base64
import backend.utils.unstructured_extractor_helpers as helpers
from backend.core.config import settings

# Function to extract elements from image pages
def element_extractor(file_path: str):
    """
    Extract elements from an image using Unstructured's partition_image function.
    Args:
        image_path (str): Path to the image file.
    Returns:
        list: List of extracted elements from the image.
    """
    print(f"file_path: {file_path}")
    if not file_path:
        raise ValueError("file_path must be provided")
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    type = file_path.split('.')[-1].lower()  # Get the file type from the extension
    
    if type == "jpeg" or type == "jpg" or type == "png":
        from unstructured.partition.image import partition_image

        image_name = os.path.basename(file_path).replace('.jpeg', '')
        image_filepath = os.path.join(
            settings.IMG_FIGURES_DIR, "figures", f"{image_name}_figures"
        )

        elements = partition_image(
            filename=file_path,
            extract_images_in_pdf=True,
            extract_image_block_to_payload=False,
            extract_image_block_output_dir=image_filepath,
            infer_table_structure=True,
            languages=["eng", "ind"]
        )
    elif type == "pdf":
        from unstructured.partition.pdf import partition_pdf

        file_name = os.path.basename(file_path).replace('.pdf', '')
        image_filepath = os.path.join(
            settings.IMG_FIGURES_DIR, "figures", f"{file_name}_figures"
        )

        raw_pdf_elements = partition_pdf(
            filename=file_path,
            extract_images_in_pdf=True,
            extract_image_block_to_payload=False,
            extract_image_block_output_dir=image_filepath,
            infer_table_structure=True,
            languages=["eng", "ind"]
        )
        elements = helpers.split_elements(raw_pdf_elements)

    elif type == "xlsx" or type == "xls":
        from unstructured.partition.xlsx import partition_xlsx

        file_name = os.path.basename(file_path).replace('.xlsx', '')
        image_filepath = os.path.join(
            settings.IMG_FIGURES_DIR, "figures", f"{file_name}_figures"
        )

        raw_xlsx_elements = partition_xlsx(
            filename=file_path,
            extract_images_in_pdf=True,
            extract_image_block_to_payload=False,
            extract_image_block_output_dir=image_filepath,
            infer_table_structure=True,
            languages=["eng", "ind"]
        )

        elements = helpers.split_elements(raw_xlsx_elements)
    return elements

# Fuction to extract metadata from Unstructured elements
def extract_unstructured_elements(elements, page_num):
    element_metadata = []
    figure_list = []
    temp_table = ""
    min_counter = 0

    # Process elements and figure relationships
    for i, element in enumerate(elements):
        unstructured_element = element.metadata.to_dict()

        if "coordinates" in unstructured_element:
            element_bbox = helpers.extract_bbox(unstructured_element["coordinates"]["points"])
        else:
            element_bbox = None

        if "unstructured.documents.elements.Image" in str(type(element)):
            image_path = unstructured_element["image_path"]

            pil_image = resize_img_from_path(image_path, size=560)

            element_metadata.append({
                "idx": i - min_counter,
                "status": "Success",
                "type": "image",
                "bbox": element_bbox,
                "text": "",
                "image_metadata": {
                    "image_type": "",
                    "caption": "",
                    "description": "",
                    "ocr_string": str(element),
                    "image_base64": image_to_base64(image_path=image_path, quality=50),
                },
            })

            figure_list.append({
                "page_num": page_num,
                "idx": i - min_counter,
                "pil_image": pil_image,
                "generated_text": "",
                "status": "Success",
            })
        else:
            if str(element).strip() == "":
                min_counter += 1
                continue

            if "unstructured.documents.elements.Table" in str(type(element)):

                md_table = markdownify.markdownify(unstructured_element["text_as_html"])
                md_table = helpers.filter_table(md_table)

                if helpers.get_len_columns(md_table) == helpers.get_len_columns(temp_table):
                    temp_table += "\n" + md_table
                    min_counter += 1
                else:
                    table = helpers.format_table(temp_table)
                    temp_table = md_table

                if i + 1 == len(elements) or "unstructured.documents.elements.Table" not in str(type(elements[i + 1])):
                    table = helpers.format_table(temp_table)
                    temp_table = ""
                elif helpers.get_len_columns(temp_table) != helpers.get_len_columns(markdownify.markdownify(elements[i+1].metadata.text_as_html)):
                    table = helpers.format_table(temp_table)
                    temp_table = ""

                if len(table) > 0:

                    # Append table metadata
                    element_metadata.append({
                        "idx": i - min_counter,
                        "status": "Success",
                        "type": "table",
                        "bbox": element_bbox,
                        "text": table,
                    })
                table = ""

            else:
                element_type = "text"

                element_metadata.append({
                    "idx": i - min_counter,
                    "status": "Success",
                    "type": element_type,
                    "bbox": element_bbox,
                    "text": str(element),
                })

    return element_metadata, figure_list

# Extract elements from PDF
def extract_elements(pages, file_path=None):
    figure_list = []
    elements = []

    print(f"Extract elements path: {file_path}")

    if not file_path:
        for i, page in enumerate(pages):
            elements.append(element_extractor(file_path=page["image"]))
    else:
        elements = element_extractor(file_path=file_path)

    for i, page in enumerate(pages):
        if i < len(elements):
            page["elements"], figures = extract_unstructured_elements(elements=elements[i], page_num=i)
            figure_list += figures
        else:
            # Handle missing elements appropriately
            page["elements"] = []
            print(f"Warning: No elements found for page index {i}")
    print(f"Extracted {len(figure_list)} figure from {len(pages)} pages.")
    return pages, figure_list

from unstructured.partition.image import partition_image
import markdownify
import re
from langchain.prompts import ChatPromptTemplate
from backend.services.model_manager import Formatter_PIPELINE

# Function to extract elements from image pages
def element_extractor(img_path):
    raw_pdf_elements = []
    print(f"img_path: {img_path}")
    for page in img_path:
        raw_pdf_element = partition_image(
            filename=page,
            extract_images_in_pdf=True,
            infer_table_structure=True,
            languages=["eng", "ind"]
        )
        raw_pdf_elements.append(raw_pdf_element)

    return raw_pdf_elements

# Extract bounding box from the element
def extract_bbox(element):
    element_metadata = element.metadata.to_dict()
    points = element_metadata["coordinates"]["points"]

    # Extract x and y coordinates from the points
    x_coords = [point[0] for point in points]
    y_coords = [point[1] for point in points]

    # Calculate the bounding box: [x1, y1, x2, y2]
    x1 = min(x_coords)
    y1 = min(y_coords)
    x2 = max(x_coords)
    y2 = max(y_coords)

    return [x1, y1, x2, y2]

# Extract elements to text and replace figures with tables
def extract_elements_to_text(elements, figures):
    figures = figures.copy()
    string: list[str] = []

    # image figures bbox
    fig_index = []
    for i, fig in enumerate(figures):
        bbox_dist = []
        fig_bbox = fig["bbox"]
        for j, element in enumerate(elements):
            if "unstructured.documents.elements.Image" in str(type(element)):
                element_bbox = extract_bbox(element)

                # calculate the distance between the figure and the element
                dist = (fig_bbox[0] - element_bbox[0]) ** 2 + (fig_bbox[1] - element_bbox[1]) ** 2
                bbox_dist.append(dist)
            else:
                bbox_dist.append(9999999999)

        # find the index of the minimum distance
        min_index = bbox_dist.index(min(bbox_dist))
        fig_index.append(min_index)

    for i, element in enumerate(elements):
        if "unstructured.documents.elements.Table" in str(type(element)):
            table = markdownify.markdownify(element.metadata.text_as_html)
            string.append(table)
        elif "unstructured.documents.elements.Image" in str(type(element)):
            # check if the element is a figure
            if i in fig_index:
                index = fig_index.index(i)
                fig = figures[index]
                # append table to text
                string.append(fig["data"])
                # remove used figure
                figures.pop(index)
                fig_index.pop(index)
            else:
                # remove the image from the text
                continue
        else:
            string.append(markdownify.markdownify(str(element), heading_style="ATX"))

    if len(figures) > 0:
        for fig in figures:
            string.append(fig["name"])
            string.append(fig["data"])

    return "\n\n".join(string)

# Extract elements from PDF
def extract_elements(pdf_path, pages):

    # Extract all elements from the PDF pages
    for page in enumerate(pages):
        element = element_extractor(pages)
        page["text"] = extract_elements_to_text(element, page["figures"])

    return pages

# Final formatting function to format the extracted text into Markdown
# Function to clean the markdown text
def clean_md(result_text):
    md_text = result_text[0]["generated_text"][-1]["content"]

    # markdown block handling
    if "```markdown" in md_text:
        # split the text by ```markdown
        md_text = md_text.split("```markdown")[1].strip()
        lines = md_text.split('\n')
        # find the last line that contains ```
        last_index = None
        for i, line in enumerate(lines):
            if line.strip() == '```':
                last_index = i
        if last_index is not None:
            # remove ``` and all lines after it
            lines = lines[:last_index]
        md_text = '\n'.join(lines)

    # mermaid block handling
    if "```mermaid" in md_text:
        lines = md_text.split('\n')
        last_arrow_index = None
        # find the last line that contains -->
        for i, line in enumerate(lines):
            if '-->' in line:
                last_arrow_index = i
        if last_arrow_index is not None:
            for j in range(last_arrow_index + 1, len(lines)):
                if lines[j].strip() == '```':
                    return md_text
            lines.insert(last_arrow_index + 1, '```')
        md_text = '\n'.join(lines)

    return md_text

# load llm model
# Prompt template
SYSTEM_FORMAT_PROMPT = """You are a helpful assistant who helps users format the extracted data from a document page into Markdown format.
You are not allowed to change or summarize the given text; only correct any broken words and delete any unsuccessful OCR results, if any"""

FORMAT_PROMPT_TEMPLATE = """Transform this extracted text data from a page into Markdown format.
Look for the possible headings or stylings in the text and tailor it to resemble a page layout, preserve the original numbering and layout (it can be in the middle of the page).
Do not change or summarize the content; only correct any broken words and delete any unsuccessful OCR results, if any.

Requirements:
- Output Only Markdown: Return solely the Markdown content without any additional explanations or comments.
- No Delimiters: Do not use code fences or delimiters like ```markdown.

Extracted Text:
{extracted_text}
"""


def format_all_data(pages):
    

    formated_text = []

    for page in pages:
        # get the text from the page
        extracted_text = page['text']

        # Create the prompt template and format the text
        prompt_template = ChatPromptTemplate.from_template(FORMAT_PROMPT_TEMPLATE)
        prompt = prompt_template.format(extracted_text=extracted_text)

        # Generate the formatted text using the LLM
        formatted_text = Formatter_PIPELINE(prompt)

        # Clean the formatted text
        formatted_text.append(clean_md(formatted_text))

    return formated_text
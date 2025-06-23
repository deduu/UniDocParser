import re
from backend.utils.helpers import process_string
from pathlib import Path
from PIL import Image
from backend.utils.helpers import process_string, resize_img
from backend.core.ft_vlm_format_config import formatter_vlm

# Combining Extracted element into text
# Function to clean the OCR text
def clean_text(ocr_text):
    # Clean broken words
    # Join hyphenated words split across lines
    ocr_text = re.sub(r'(\w)-\s*\s(\w)', r'\1\2', ocr_text)

    # Fix common incorrect punctuation, such as double commas or periods
    # Replace consecutive dots with a single dot
    ocr_text = re.sub(r'\.\.+', '.', ocr_text)
    # Replace consecutive commas with a single comma
    ocr_text = re.sub(r'\,\,+', ',', ocr_text)

    # # Remove extra line breaks
    # ocr_text = re.sub(r'\n+', '\n', ocr_text)  # Clean multiple newlines

    # Join broken paragraphs newlines even if they are punctuated
    ocr_text = re.sub(
        r'([\w/,’' + r"'" + r'"\s])\s([a-z,\("' + r'“‘' + r'])', r'\1 \2', ocr_text)
    ocr_text = re.sub(r'([,=_])\s([a-z0-9"“‘])', r'\1 \2', ocr_text)

    # Remove spaces before and after all punctuation marks
    ocr_text = re.sub(r'\s+([.,!?%\'\)\]])', r'\1',ocr_text)    # Remove spaces before punctuation

    # Remove spaces after opening brackets
    ocr_text = re.sub(r'([\(\[])\s+', r'\1', ocr_text)

    # Encode `` and '' as quotation marks
    ocr_text = re.sub(r'`` ', '"', ocr_text)
    ocr_text = re.sub(r"''", '"', ocr_text)

    return ocr_text

# Function to process the extracted text
def format_extracted_text(pages):
    for i, page in enumerate(pages):
        text = ""
        # fig_caption = ""
        # fig_bbox = []

        # for j, element in enumerate(page['elements']):
        #     if element['type'] == 'image':
        #         fig_caption = element['image_metadata']['caption']
        #         fig_bbox = element['bbox']
        #         bbox_idx = j
        #     else:
        #         # if len text < 2 delete the text element
        #         if len(element['text']) < 2:
        #             del page['elements'][j]
        #             continue
        #         # check if the text is in figures
        #         elif len(fig_bbox) > 0:
        #             # check if the text is in figures
        #             in_bbox = False

        #             if (element['bbox'][0] >= fig_bbox[0] and element['bbox'][1] >= fig_bbox[1] and
        #                     element['bbox'][2] <= fig_bbox[2] and element['bbox'][3] <= fig_bbox[3]):
        #                 in_bbox = True

        #             if in_bbox:
        #                 processed_text = process_string(element['text'])
        #                 processed_fig_caption = process_string(fig_caption)
        #                 # check if the text is in the figure caption
        #                 if processed_fig_caption in processed_text or processed_text in processed_fig_caption:
        #                     # reorder figure name to exactly after the Image element
        #                     element_metadata = page['elements'][j].copy()

        #                     # delete the text element from the page
        #                     del page['elements'][j]

        #                     # insert the element_metadata to the page after the image element
        #                     page['elements'].insert(
        #                         bbox_idx + 1, element_metadata)
        #                 else:
        #                     # delete the text element from the page
        #                     del page['elements'][j]

        for element in page['elements']:
            text += f"{element['text']}\n\n"

        # clean the text
        page["text"] = clean_text(text)
        page["markdown"] = clean_text(text)

    return pages

# Final formatting function to format the extracted text into Markdown
# Function to clean the markdown text
def clean_md(result_text):
    md_text = result_text

    # remove all code blocks
    if "```" in md_text and not ("```markdown" in md_text or "```mermaid" in md_text):
        md_text  = re.sub(r'```', '', md_text)

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

    # remove the "Extracted Text:" part
    if "Extracted Text:" in md_text:
        md_text = md_text.split("Extracted Text:")[1].strip()

    if "<|im_end|>" in md_text:
        # split the text by
        md_text = md_text.split("<|im_end|>")[0].strip()

    return md_text


# load llm model
TMP_DIR = Path("./tmp")            # ←  centralise tmp folder
TMP_DIR.mkdir(exist_ok=True)       # ←  create once


def format_markdown(pages: list[dict], pdf_name: str) -> list[dict]:
    """
    • Resizes page snapshot to 1080 px width (keeps aspect ratio)
    • Saves the resized image under ./tmp/
    • Calls VLM to generate markdown and stores it back into the page
    """
    for page in pages:
        idx = page["index"]
        print(f"Processing {pdf_name} page {idx}")

        # -------- 1. load & resize image ---------------------------------
        pil_image = Image.open(page["image"])
        pil_image = resize_img(pil_image, size=1080)

        # -------- 3. run VLM formatter -----------------------------------
        extracted_text = page["text"]
        output = formatter_vlm.generate(
            extracted_text=extracted_text, 
            image=pil_image
        )

        # -------- 4. post-process & store --------------------------------
        page["markdown"] = clean_md(output)

    return pages
import re
from pathlib import Path
from PIL import Image
from backend.utils.helpers import resize_img

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


def format_markdown(formatter_model, pages: list[dict], pdf_name: str) -> list[dict]:
    """
    • Resizes page snapshot to 1080 px width (keeps aspect ratio)
    • Saves the resized image under ./tmp/
    • Calls VLM to generate markdown and stores it back into the page
    """
    for page in pages:
        idx = page["index"]

        # -------- 1. load & resize image ---------------------------------
        pil_image = Image.open(page["image"])
        pil_image = resize_img(pil_image, size=1080)

        # -------- 3. run VLM formatter -----------------------------------
        extracted_text = page["text"]
        output, status = formatter_model.generate(
            extracted_text=extracted_text, 
            image=pil_image
        )
        page["status"] = status

        # -------- 4. post-process & store --------------------------------
        if status == "Success":
            print(f"{pdf_name} page {idx} successfully formatted.")
            page["markdown"] = clean_md(output)
        else:
            print(f"{pdf_name} page {idx} formatting failed, using raw text.")
            page["markdown"] = page["text"]
        
    
    return pages
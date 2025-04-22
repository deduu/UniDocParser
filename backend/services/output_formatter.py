import re
from langchain.prompts import ChatPromptTemplate
from backend.services.model_manager import Formatter_PIPELINE
from backend.utils.helpers import process_string

# Combining Extracted element into text
# Function to clean the OCR text
def clean_text(ocr_text):
    # Clean broken words
    # Join hyphenated words split across lines
    ocr_text = re.sub(r'(\w)-\s*\s(\w)', r'\1\2', ocr_text)

    # Fix common incorrect punctuation, such as double commas or periods
    ocr_text = re.sub(r'\.\.+', '.', ocr_text)  # Replace consecutive dots with a single dot
    ocr_text = re.sub(r'\,\,+', ',', ocr_text)  # Replace consecutive commas with a single comma

    # # Remove extra line breaks
    # ocr_text = re.sub(r'\n+', '\n', ocr_text)  # Clean multiple newlines

    # Join broken paragraphs newlines even if they are punctuated
    ocr_text = re.sub(r'([\w/,’' + r"'" + r'"\s])\s([a-z,\("' + r'“‘' + r'])', r'\1 \2', ocr_text)
    ocr_text = re.sub(r'([,=_])\s([a-z0-9"“‘])', r'\1 \2', ocr_text)

    # Remove spaces before and after all punctuation marks
    ocr_text = re.sub(r'\s+([.,!?%\'\)\]])', r'\1', ocr_text)    # Remove spaces before punctuation
    ocr_text = re.sub(r'([\(\[])\s+', r'\1', ocr_text)           # Remove spaces after opening brackets

    # Encode `` and '' as quotation marks
    ocr_text = re.sub(r'`` ', '"', ocr_text)
    ocr_text = re.sub(r"''", '"', ocr_text)

    return ocr_text

def format_extracted_text(pages):
    for i, page in enumerate(pages):
        text = ""
        fig_caption = ""
        fig_bbox = []

        for j, element in enumerate(page['elements']):
            if element['type'] == 'image':
                fig_caption = element['caption']
                fig_bbox = element['bbox']
                bbox_idx = j
            else:
                # if len text < 2 delete the text element
                if len(element['text']) < 2:
                    del page['elements'][j]
                    continue
                # check if the text is in figures
                elif len(fig_bbox) > 0:
                    # check if the text is in figures
                    in_bbox = False

                    if (element['bbox'][0] >= fig_bbox[0] and element['bbox'][1] >= fig_bbox[1] and
                        element['bbox'][2] <= fig_bbox[2] and element['bbox'][3] <= fig_bbox[3]):
                        in_bbox = True

                    if in_bbox:
                        processed_text = process_string(element['text'])
                        processed_fig_caption = process_string(fig_caption)
                        # check if the text is in the figure caption
                        if processed_fig_caption in processed_text or processed_text in processed_fig_caption:
                            # reorder figure name to exactly after the Image element
                            element_metadata = page['elements'][j].copy()

                            # delete the text element from the page
                            del page['elements'][j]

                            # insert the element_metadata to the page after the image element
                            page['elements'].insert(bbox_idx + 1, element_metadata)
                        else:
                            # delete the text element from the page
                            del page['elements'][j]
            
            text += f"{element['text']}\n\n"

        # clean the text
        page["text"] = clean_text(text)

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
SYSTEM_FORMAT_PROMPT = """You are a helpful assistant who helps users format the extracted data from a document page image into Markdown format.
You are not allowed to change or summarize the given text; only reorder the wrong paragraph order, correct any broken words, and delete any unsuccessful OCR results, if any."""

FORMAT_PROMPT_TEMPLATE = """Transform the extracted text data from a page into Markdown format.
Identify any possible headings or styles within the text and adjust it to create a page layout that resembles the original.
Ensure that you maintain the original numbering and overall structure from the provided page image, and arrange the extracted text in an order that reflects the reading sequence.

Requirements:
- Output Only Markdown: Return solely the Markdown content without any additional explanations or comments.
- No Delimiters: Do not use code fences or delimiters like ```markdown.

Extracted Text:
{extracted_text}
"""

def format_markdown(pages):
    for i, page in enumerate(pages):
        print(f"Formatting Page {i}")
        # get the text from the page
        extracted_text = page['text']
        image = page['image']

        # Create the prompt template and format the text
        prompt_template = ChatPromptTemplate.from_template(FORMAT_PROMPT_TEMPLATE)
        prompt = prompt_template.format(extracted_text=extracted_text)

        messages = [
            {
                "role": "system",
                "content": [
                    {"type": "text", "text": SYSTEM_FORMAT_PROMPT}
                ]
            },
            {
                "role": "user",
                "content": [
                    {"type": "image", "image": image},
                    {"type": "text", "text": prompt}
                ]
            }
        ]

        # Generate the formatted text using the LLM
        formatted_text = Formatter_PIPELINE(messages)

        # Clean the formatted text
        page["markdown"] = (clean_md(formatted_text))

    return pages
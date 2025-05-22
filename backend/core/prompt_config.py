from langchain.prompts import ChatPromptTemplate

SYSTEM_FIG_TEMPLATE = """You are a helpful assistant focused on converting images into easily understandable formats. Follow these steps:
Classify the image:
- If the image is a graph/chart, identify the type and convert the data into a structured table in Markdown format, providing a brief context or analysis.
- If the image is a flowchart, convert it into Mermaid code, accompanied by a brief explanation or analysis.
- If the image is not a graph/chart or flowchart, provide a concise description of the image's content using short sentences.
- If the image is a logo, write the description as the company name without any explanation.
If the image contains caption or title, include it fully in the output. If not available, leave it blank.
"""

FIG_PROMPT_TEMPLATE = """Convert the provided figure image into an understandable format.

---

Output format if the image a chart/graph:
- Figure Caption: (image caption or title if available, otherwise "image")
- Type: (Bar Chart, Line Graph, Pie Chart, etc.)
data:
| Structured Table Data |
enddata;
- Short Description: …

---

Output format if the image is a flowchart:
- Figure Caption: (image caption or title if available, otherwise "image")
- Type: Flowchart
data:
```mermaid
Mermaid Code
```
enddata;
- Short Description: …

---

Output format if another image:
- Figure Caption: (image caption or title if available, otherwise "image")
- Type: …
- Short Description: (Short description of the image, if it is a logo just write the company name)
"""

# Default Prompt for VLM Markdown Formatting
SYSTEM_FORMAT_PROMPT = """You are a helpful assistant who helps users format the extracted data from a document page image into Markdown format.
You are not allowed to change or summarize the given text; only reorder the wrong paragraph order, correct any broken words, and delete any unsuccessful OCR results, if any."""

FORMAT_PROMPT_TEMPLATE = """Transform the extracted text and structured data from a page into Markdown format based on the image.
Identify any possible headings or styles within the text and adjust it to create a page layout that resembles the original page.
Sometimes there will be a failure in table extraction, fix it. Example:
| Category | %  |
|----------|----|
| A        | 50 |
| B        | 50 |
ActualCategory1 ActualCategory2

Ensure that you maintain the original numbering and overall structure from the provided page image, and arrange the extracted text and structured data in an order that reflects the reading sequence.

Requirements:
- Output Only Markdown: Return solely the Markdown content without any additional explanations or comments.
- No Delimiters: Do not use code fences or delimiters like ```markdown.

Extracted Text:
"""

class Fig2Text_Prompt:
    def __init__(
        self,
        system_prompt=SYSTEM_FIG_TEMPLATE,
        prompt=FIG_PROMPT_TEMPLATE,
    ):
        self.system_prompt = system_prompt
        self.prompt = prompt

    def get_system_prompt(self):
        return self.system_prompt

    def get_prompt(self):
        return self.prompt
    
class Formatter_Prompt:
    def __init__(
        self,
        system_prompt=SYSTEM_FORMAT_PROMPT,
        prompt=FORMAT_PROMPT_TEMPLATE,
    ):
        self.system_prompt = system_prompt
        self.prompt = prompt

    def get_system_prompt(self):
        return self.system_prompt

    def get_prompt(self, extracted_text):
        user_prompt = self.prompt + extracted_text

        return user_prompt
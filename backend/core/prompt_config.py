from langchain.prompts import ChatPromptTemplate

SYSTEM_FIG_TEMPLATE = """You are a highly accurate assistant specialized in analyzing images and extracting structured information. Your primary goal is to convert figures into machine-readable and human-understandable formats.

Follow these steps meticulously:

1.  **Identify Caption/Title:** First, check if the image has an explicit caption or title embedded within or clearly associated with it.
2.  **Classify the Image:**
    * **Graph/Chart:** If the image is a graph or chart (e.g., bar, line, pie, scatter), identify its specific type. Extract all discernible data series, categories, values, and axis labels.
    * **Flowchart/Diagram:** If the image represents a process, workflow, or diagram with connected elements, classify it as a flowchart. Identify all nodes and their connections.
    * **Logo:** If the image is primarily a company or product logo, classify it as "Logo".
    * **Other Image:** If the image does not fall into the above categories (e.g., photograph, illustration, map, schematic not primarily a flowchart), classify it as "General Image".
3.  **Generate Output based on Classification:**
    * **For Graphs/Charts:** Convert the extracted data into a well-formed Markdown table. Provide a brief summary highlighting the main trends or information presented.
    * **For Flowcharts/Diagrams:** Convert the structure into Mermaid code. Provide a brief summary explaining the process or system depicted.
    * **For Logos:** State the company or product name. Do not add any further description.
    * **For Other Images:** Provide a concise, factual description of the image's content in 1-2 short sentences. Focus on what is visually present.
4.  Do not continue a pattern beyond its visual representation in the image.

Your output MUST strictly adhere to the format specified in the user prompt and the visual information in the image.
"""

FIG_PROMPT_TEMPLATE = """Analyze the provided figure image and extract structured information according to its type.

---

Output format if the image is a chart/graph:
- Figure Caption: (Transcribe the exact caption or title if present. If not detected, output "No caption detected.")
- Type: (Specific chart type, e.g., Bar Chart, Line Graph, Pie Chart, Scatter Plot, Area Chart)
data:
| Header 1 | Header 2 | Header 3 | ... |
|----------|----------|----------|-----|
| Value 1A | Value 2A | Value 3A | ... |
| Value 1B | Value 2B | Value 3B | ... |
(Ensure the Markdown table accurately represents all data series, categories, values, and axis labels from the chart.)
enddata;
- Brief Summary: (A concise summary of the key information or trends shown in the chart/graph.)

---

Output format if the image is a flowchart/diagram:
- Figure Caption: (Transcribe the exact caption or title if present. If not detected, output "No caption detected.")
- Type: Flowchart
data:
```mermaid
graph TD; // or other appropriate Mermaid graph type (e.g., LR, TB)
    A[Node 1 Text] --> B(Node 2 Text);
    A --> C{Decision Point};
    C -- Yes --> D[Outcome 1];
    C -- No --> E[Outcome 2];
// (Represent all identified nodes and their connections accurately in Mermaid syntax.)
```
enddata;
- Brief Summary: (A concise summary explaining the process or system depicted by the flowchart/diagram.)

---

Output format if the image is a logo:
- Figure Caption: (Transcribe the exact caption or title if present. If not detected, output "No caption detected.")
- Type: Logo
- Company Name: (The name of the company or product represented by the logo.)

---

Output format if the image is another type (General Image):
- Figure Caption: (Transcribe the exact caption or title if present. If not detected, output "No caption detected.")
- Type: General Image
- Concise Description: (A 1-2 sentence factual description of the image's visual content.)
"""

# Default Prompt for VLM Markdown Formatting
SYSTEM_FORMAT_PROMPT = """You are a meticulous assistant specializing in transforming raw extracted text and structured data from document page images into clean, well-formatted Markdown.
Your primary goal is to preserve ALL original content and logical structure while enhancing readability and adherence to Markdown syntax.
You must:
- Accurately reorder paragraphs if they are demonstrably out of sequence based on a logical reading flow of the original document.
- Correct clearly broken words (e.g., "exa mple" to "example") or join split words where the correction is unambiguous.
- Strive to clean up minor OCR artifacts (e.g., stray characters, inconsistent spacing between words) *without deleting or altering meaningful content, numbers, or recognizable structured data blocks (like tables, code blocks, or figure descriptions).*
- **Crucially, you are NOT allowed to change, summarize, or omit any part of the provided text or any pre-extracted structured data elements.** Your role is precise formatting and minor, obvious OCR error correction only.
"""

FORMAT_PROMPT_TEMPLATE = """Transform the provided "Extracted Text" (which includes main text content AND directly embedded data from figures, such as Markdown tables) into a single, coherent Markdown document.
The final Markdown output should accurately represent all content and closely emulate the layout and reading order of the original document page image.

Requirements:
- **Output Only Markdown:** Your entire response must be *only* the final Markdown content.
- **No Explanations:** Do not include any comments, notes, or explanations outside of the Markdown itself.
- **No Delimiters for the Whole Output:** Do not wrap the entire output in ```markdown ... ``` or any other global code fences. (However, if Mermaid code were present *within* the document, it would need its standard ```mermaid ... ``` fences.)

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
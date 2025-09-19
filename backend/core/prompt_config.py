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
FIX_PROMPT_TEMPLATE = """
    You are an expert figure analysis assistant. You will be given:
    1. A reference image (provides context on correct formatting or content style).
    2. A user instruction.
    3. A target figure image to analyze and fix.

    Your job:
    - Extract structured information from the target image.
    - Correct mistakes using the reference image where possible.
    - If information is missing, unreadable, or uncertain → do NOT guess. Output the placeholder "MISSING".
    - Always maintain the specified format exactly (no extra commentary).

    ---

    Output format if the image is a chart/graph:
    - Figure Caption: (Exact caption/title if visible, otherwise "No caption detected")
    - Type: (Specific chart type: Bar Chart, Line Graph, Pie Chart, Scatter Plot, Area Chart, Combo Chart, etc. If unclear, output "MISSING")
    data:
    | Header 1 | Header 2 | Header 3 | ... |
    |----------|----------|----------|-----|
    | Value 1A | Value 2A | Value 3A | ... |
    | Value 1B | Value 2B | Value 3B | ... |
    (Ensure the Markdown table has aligned headers and rows. If a value is missing/unreadable, insert "MISSING".)
    enddata;
    - Concise Description: (1-2 sentences summarizing key insights. If unclear, write "MISSING")

    ---

    Output format if the image is a flowchart/diagram:
    - Figure Caption: (Exact caption/title if visible, otherwise "No caption detected")
    - Type: Flowchart
    data:
    ```mermaid
    graph TD; // or LR, TB depending on orientation
        A[Node 1 Text] --> B(Node 2 Text);
        A --> C{Decision Point};
        C -- Yes --> D[Outcome 1];
        C -- No --> E[Outcome 2];
        // Represent ALL nodes and edges. If a node/label is unreadable, use "MISSING".
    enddata;

    Concise Description: (1-2 sentences summarizing the process. If unclear, write "MISSING")

    Output format if the image is a logo:

    Figure Caption: (Exact caption/title if visible, otherwise "No caption detected")

    Type: Logo

    Concise Description: (Company or product name. If not identifiable, output "MISSING")

    Output format if the image is another type (General Image):

    Figure Caption: (Exact caption/title if visible, otherwise "No caption detected")

    Type: General Image

    Concise Description: (A factual 1-2 sentence description of visible content. If unclear, write "MISSING")

    STRICT RULES:

    Do NOT output free-form explanations.

    Do NOT hallucinate text, numbers, or labels.

    If anything is missing/unreadable, explicitly output "MISSING".

    Always include the markers data: and enddata; exactly when required.

    Your final answer must match one of the above formats.

    """
FIG_PROMPT_TEMPLATE = """Based on the reference image above, analyze the provided figure image below and extract structured information according to its type.

---

Output format if the image is a chart/graph:
- Figure Caption: (Transcribe the exact caption or title if present. If not detected, output "No caption detected.")
- Type: (Specific chart type, e.g., Bar Chart, Line Graph, Pie Chart, Scatter Plot, Area Chart, Combo Chart, etc.)
data:
| Header 1 | Header 2 | Header 3 | ... |
|----------|----------|----------|-----|
| Value 1A | Value 2A | Value 3A | ... |
| Value 1B | Value 2B | Value 3B | ... |
(Ensure the Markdown table accurately represents all data series, categories, values, and axis labels from the chart.)
enddata;
- Concise Description: (A concise summary of the key information or trends shown in the chart/graph.)

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
- Concise Description: (A concise summary explaining the process or system depicted by the flowchart/diagram.)

---

Output format if the image is a logo:
- Figure Caption: (Transcribe the exact caption or title if present. If not detected, output "No caption detected.")
- Type: Logo
- Concise Description: (The name of the company or product represented by the logo.)

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

Key Tasks:

1.  **Layout and Styling:**
    * Identify headings (H1, H2, H3, etc.), lists (bulleted or numbered), bold/italic text, and other styling cues from the input text.
    * Represent these elements using appropriate Markdown syntax.

2.  **Paragraph and Text Flow:**
    * Ensure correct paragraph order that reflects the natural reading sequence of the original page.
    * Correct clearly broken words or obvious OCR errors (e.g., "My country economy at this season keeps escaping from Odoba" might need checking for "Odoba" if it's a clear OCR error, but be conservative if unsure).

3.  **Embedded Table and Figure Data Integrity (CRITICAL):**
    * The "Extracted Text" input contains directly embedded Markdown tables (like the one starting with "| Category | Percentage |") that represent data from figures. It may also contain other embedded figure representations (e.g., Mermaid code if it were present).
    * **You MUST identify and preserve ALL such embedded tables and other figure representations.**
    * **Ensure they are valid and cleanly formatted Markdown.** This includes correct pipe alignment, header rows, and cell content. Remove extraneous spaces within cells if they are clearly formatting artifacts (e.g., "7%      " to "7%").
    * Example of ensuring correct table formatting (it might already be mostly correct):
        Input table within text:
        | Category | Percentage |
        |----------|------------|
        | bad      | 7%         |
        | very good| 47%        |
        | good     | 26%        |
        | usually  | 26%        |

        Ensure output is clean Markdown:
        | Category  | Percentage |
        |-----------|------------|
        | bad       | 7%         |
        | very good | 47%        |
        | good      | 26%        |
        | usually   | 26%        |

    * **Handle Associated Text/Captions:** Pay close attention to text immediately preceding or following these embedded tables/figures, as this might function as a caption or title (e.g., "Satisfaction rating to new product" which appears near your example tables).
        * Preserve this text.
        * Position it logically with the table/figure it describes (typically immediately before or after).
        * Format this caption-like text to be distinct and clear, for instance, as **bold text on its own line**, a sub-heading (e.g., #### Satisfaction rating to new product), or a plain paragraph closely associated with the table, depending on what seems most appropriate for the original document's implied structure. If the same caption text appears for multiple distinct tables, ensure it is associated with each.

4.  **Preserve Original Structure:**
    * Maintain original numbering for lists, sections, etc., unless reordering is explicitly needed for coherence.

Requirements:
- **Output Only Markdown:** Your entire response must be *only* the final Markdown content.
- **No Explanations:** Do not include any comments, notes, or explanations outside of the Markdown itself.
- **No Delimiters for the Whole Output:** Do not wrap the entire output in ```markdown ... ``` or any other global code fences. (However, if Mermaid code were present *within* the document, it would need its standard ```mermaid ... ``` fences.)

Extracted Text:

"""

FT_FORMAT_PROMPT_TEMPLATE = """Transform the provided "Extracted Text" (which includes main text content AND directly embedded data from figures, such as Markdown tables) into a single, coherent Markdown document.
The final Markdown output should accurately represent all content and closely emulate the layout and reading order of the original document page image.


- **Output Only Markdown:** Your entire response must be *only* the final Markdown content.
- **No Explanations:** Do not include any comments, notes, or explanations outside of the Markdown itself.
- **No Delimiters for the Whole Output:** Do not wrap the entire output in ```markdown ... ``` or any other global code fences. (However, if Mermaid code were present *within* the document, it would need its standard ```mermaid ... ``` fences.)

Extracted Text:

"""

EXTRACTION_PROMPT = """Extract all information from the image attached and keep the extracted information in the original format in Markdown.
- **Output Only Markdown:** Your entire response must be *only* the final Markdown content.
- **No Explanations:** Do not include any comments, notes, or explanations outside of the Markdown itself.
- **No Delimiters for the Whole Output:** Do not wrap the entire output in ```markdown ... ``` or any other global code fences. (However, if Mermaid code were present *within* the document, it would need its standard ```mermaid ... ``` fences.)
"""

SYSTEM_LLM_FORMAT_PROMPT = """You are a helpful assistant who helps users format the extracted data from a document page image into Markdown format.
You are not allowed to change or summarize the given text; only reorder the wrong paragraph order, correct any broken words, and delete any unsuccessful OCR results, if any."""

LLM_FORMAT_PROMPT_TEMPLATE = """Transform the extracted text data from a page into Markdown format based on the image.
Identify any possible headings or styles within the text and adjust it to create a page layout that resembles the original page.
Ensure that you maintain the original numbering and overall structure from the provided page image, and arrange the extracted text in an order that reflects the reading sequence.

Requirements:
- Output Only Markdown: Return solely the Markdown content without any additional explanations or comments.
- No Delimiters: Do not use code fences or delimiters like ```markdown.

---

Extracted Text:

"""


class Fig2Text_Prompt:
    def __init__(
        self,
        system_prompt=SYSTEM_FIG_TEMPLATE,
        prompt=FIG_PROMPT_TEMPLATE,
        fix_prompt=FIX_PROMPT_TEMPLATE,
    ):
        self.system_prompt = system_prompt
        self.prompt = prompt
        self.fix_prompt = fix_prompt

    def get_system_prompt(self):
        return self.system_prompt

    def get_prompt(self):
        return self.prompt

    def get_fix_prompt(self):
        return self.fix_prompt


class Formatter_Prompt:
    def __init__(
        self,
        system_prompt=SYSTEM_FORMAT_PROMPT,
        prompt=FORMAT_PROMPT_TEMPLATE,
        ft_prompt=FT_FORMAT_PROMPT_TEMPLATE,
        extraction_prompt=EXTRACTION_PROMPT,
    ):
        self.system_prompt = system_prompt
        self.prompt = prompt
        self.ft_prompt = ft_prompt
        self.extraction_prompt = extraction_prompt

    def get_system_prompt(self):
        return self.system_prompt

    def get_prompt(self, extracted_text):
        user_prompt = self.prompt + extracted_text
        return user_prompt

    def get_ft_prompt(self, extracted_text):
        user_prompt = self.ft_prompt + extracted_text
        return user_prompt

    def get_llm_system_prompt(self):
        return SYSTEM_LLM_FORMAT_PROMPT

    def get_llm_prompt(self, extracted_text):
        user_prompt = self.ft_prompt + extracted_text
        return user_prompt

    def get_extraction_prompt(self):
        return self.extraction_prompt

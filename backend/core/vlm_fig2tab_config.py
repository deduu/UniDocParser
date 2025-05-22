import torch
from transformers import pipeline

# Default VLM Model ID
Fig2Tab_MODEL_ID = "Qwen/Qwen2.5-VL-7B-Instruct"

# Default Prompt for VLM Fig2Tab
SYSTEM_FIG_TEMPLATE = """You are a helpful assistant focused on converting images into easily understandable formats. Follow these steps:
Classify the image:
- If the image is a graph/chart, identify the type and convert the data into a structured table in Markdown format, providing a brief context or analysis.
- If the image is a flowchart, convert it into Mermaid code, accompanied by a brief explanation or analysis.
- If the image is not a graph/chart or flowchart, provide a concise description of the image's content using short sentences.
- If the image is a logo, write the description as the company name without any explanation.
If the image contains caption or title, include it fully in the output. If not available, leave it blank.
"""

PROMPT_FIG_TEMPLATE = """Convert the provided figure image into an understandable format.

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

# VLM Fig2Tab class


class Fig2Tab_PIPELINE:
    def __init__(
        self,
        model_id=Fig2Tab_MODEL_ID,
        device="cuda:0" if torch.cuda.is_available() else "cpu",
        max_new_tokens=1024,
        batch_size=1,   # Adjust batch size as needed
        system_prompt=SYSTEM_FIG_TEMPLATE,
        prompt=PROMPT_FIG_TEMPLATE
    ):
        self.system_prompt = system_prompt
        self.prompt = prompt
        # self.tokenizer = AutoTokenizer.from_pretrained(model_id)
        self.model = pipeline(
            "image-text-to-text",
            model=model_id,
            device=device,
            torch_dtype=torch.bfloat16,
            max_new_tokens=max_new_tokens,
            batch_size=batch_size,
        )

    def generate(self, images: list):
        """
        Process a list of images and return the results.
        """
        messages = []
        for i, image in enumerate(images):
            messages.append([
                {
                    "role": "system",
                    "content": [
                        {"type": "text", "text": SYSTEM_FIG_TEMPLATE}
                    ]
                },
                {
                    "role": "user",
                    "content": [
                        {"type": "image", "image": image},
                        {"type": "text", "text": PROMPT_FIG_TEMPLATE}
                    ]
                }
            ])
        output = self.model(text=messages)
        generated_text = []
        for out in output:
            generated_text.append(out[0]["generated_text"][-1]["content"])
        return generated_text


fig2tab_vlm = Fig2Tab_PIPELINE()

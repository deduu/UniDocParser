import torch
from transformers import pipeline
from langchain.prompts import ChatPromptTemplate
from backend.utils.helpers import process_string, resize_img

# Default VLM Model ID
FORMATTER_MODEL_ID = "Qwen/Qwen2.5-VL-7B-Instruct"

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
{extracted_text}
"""

# VLM Formatter class
class Formatter_PIPELINE:
    def __init__(
        self,
        model_id=FORMATTER_MODEL_ID,
        device="cuda:1" if torch.cuda.is_available() else "cpu",
        do_sample=True,
        temperature=0.3,
        top_p=0.5,
        max_new_tokens=4096,
        system_prompt=SYSTEM_FORMAT_PROMPT, 
        prompt=FORMAT_PROMPT_TEMPLATE
    ):
        self.system_prompt = system_prompt
        self.prompt = prompt
        self.model = pipeline(
            "image-text-to-text",
            model=model_id,
            device=device,
            torch_dtype=torch.bfloat16,
            max_new_tokens=max_new_tokens,
        )
        self.generate_kwargs = {
            "do_sample": do_sample,
            "temperature": temperature,
            "top_p": top_p,
            "max_new_tokens": max_new_tokens,
        }

    def generate(self, extracted_text: str, image):
        """
        Process a list of images and return the results.
        """
        # create the prompt
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
        output = self.model(text=messages, generate_kwargs=self.generate_kwargs)
        generated_text = output[0]["generated_text"][-1]["content"]
        return generated_text
    
formatter_vlm = Formatter_PIPELINE()
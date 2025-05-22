import torch
from transformers import pipeline
from langchain.prompts import ChatPromptTemplate
from backend.utils.helpers import process_string, resize_img
from backend.core.prompt_config import Formatter_Prompt

# Create a prompt instance
prompt = Formatter_Prompt()

# VLM Formatter class
class Formatter_PIPELINE:
    def __init__(
        self,
        model_id="Qwen/Qwen2.5-VL-7B-Instruct",
        device="cuda:1" if torch.cuda.is_available() else "cpu",
        do_sample=True,
        temperature=0.3,
        top_p=0.5,
        max_new_tokens=4096,
        system_prompt=prompt.get_system_prompt(), 
        prompt=prompt.get_prompt()
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
        prompt_template = ChatPromptTemplate.from_template(self.prompt)
        prompt = prompt_template.format(extracted_text=extracted_text)
        messages = [
            {
                "role": "system",
                "content": [
                    {"type": "text", "text": self.prompt}
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
import torch
from transformers import pipeline, AutoProcessor
from backend.core.vlm_config.prompt_config import Formatter_Prompt

# Create a prompt instance
prompt = Formatter_Prompt()

# VLM Formatter class
class VLM_Formatter_PIPELINE:
    def __init__(
        self,
        model_id="Qwen/Qwen2.5-VL-7B-Instruct",
        device="cuda" if torch.cuda.is_available() else "cpu",
        do_sample=True,
        temperature=0.3,
        top_p=0.5,
        min_p=0.1,
        max_new_tokens=8192,  # Adjust as needed
    ):
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
            # "min_p": min_p,
            "max_new_tokens": max_new_tokens,
        }
        self.processor = AutoProcessor.from_pretrained(model_id)
        self.max_new_tokens = max_new_tokens

    def generate(self, extracted_text: str, image):
        """
        Process a list of images and return the results.
        """
        # create the prompt
        messages = [
            {
                "role": "system",
                "content": [
                    {"type": "text", "text": prompt.get_system_prompt()}
                ]
            },
            {
                "role": "user",
                "content": [
                    {"type": "image", "image": image},
                    {"type": "text", "text": prompt.get_prompt(extracted_text)}
                ]
            }
        ]
        output = self.model(text=messages, generate_kwargs=self.generate_kwargs)
        generated_text = output[0]["generated_text"][-1]["content"]

        output_token = self.processor(text=generated_text, return_tensors="pt").input_ids
        len_output = output_token.shape[1]
        if len_output >= self.max_new_tokens - 5:
            status = "Failed"
        else:
            status = "Success"

        return generated_text, status
    
# formatter_vlm = Formatter_PIPELINE()
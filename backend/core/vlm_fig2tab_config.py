import torch
from transformers import pipeline
from backend.core.prompt_config import Fig2Text_Prompt

# Create a prompt instance
prompt = Fig2Text_Prompt()

# VLM Fig2Tab class
class Fig2Tab_PIPELINE:
    def __init__(
        self, 
        model_id="Qwen/Qwen2.5-VL-7B-Instruct",
        device="cuda:1" if torch.cuda.is_available() else "cpu",
        max_new_tokens=1024,
        batch_size=1,   # Adjust batch size as needed
    ):
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
                        {"type": "text", "text": prompt.get_system_prompt()}
                    ]
                },
                {
                    "role": "user",
                    "content": [
                        {"type": "image", "image": image},
                        {"type": "text", "text": prompt.get_prompt()}
                    ]
                }
            ])
        output = self.model(text=messages)
        generated_text = []
        for out in output:
            generated_text.append(out[0]["generated_text"][-1]["content"])
        return generated_text

fig2tab_vlm = Fig2Tab_PIPELINE()
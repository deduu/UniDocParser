import torch
from unsloth import FastVisionModel
from backend.core.prompt_config import Formatter_Prompt

fine_tuned_model_list = [
    # Gemma 3
    "ZeArkh/gemma-3-4b-it-unsloth-Markdown-Formatter",

    # Llama 3.2
    "ZeArkh/Llama-3.2-11B-Vision-Instruct-unsloth-Markdown-Formatter",

    # Qwen 2.5 VL
    "ZeArkh/Qwen2.5-VL-7B-Instruct-unsloth-Markdown-Formatter",
    "ZeArkh/Qwen2.5-VL-7B-Instruct-bnb-4bit-unsloth-Markdown-Formatter",
]

# Create a prompt instance
prompt = Formatter_Prompt()

# VLM Formatter class
class FT_Formatter_PIPELINE:
    def __init__(
        self,
        model_id="ZeArkh/Qwen2.5-VL-7B-Instruct-unsloth-Markdown-Formatter",
        device="cuda:3" if torch.cuda.is_available() else "cpu",
    ):
        self.device = device
        self.model, self.processor = FastVisionModel.from_pretrained(
            model_name=model_id,
            load_in_4bit=False,
            device_map=self.device,
        )
        FastVisionModel.for_inference(self.model) # Enable for inference!

    def generate(self, extracted_text: str, image):
        """
        Process a list of images and return the results.
        """
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "image"},
                    {"type": "text", "text": prompt.get_ft_prompt(extracted_text)},
                ]
            }
        ]

        input_text = self.processor.apply_chat_template(
            messages, add_generation_prompt = True
        )

        inputs = self.processor(
            image,
            input_text,
            add_special_tokens = False,
            return_tensors = "pt",
        ).to(self.model.device)

        generated_ids = self.model.generate(
            **inputs, 
            max_new_tokens = 8 * 1024,  # 8k tokens
            
            use_cache = True, 
            temperature = 1.5, 
            min_p = 0.1
        )

        trimmed_generated_ids = [
            out_ids[len(in_ids):] for in_ids, out_ids in zip(inputs.input_ids, generated_ids)
        ]

        output_text = self.processor.batch_decode(
            trimmed_generated_ids,
            skip_special_tokens=True,
            clean_up_tokenization_spaces=False
        )

        return output_text[0]
    
formatter_vlm = FT_Formatter_PIPELINE()
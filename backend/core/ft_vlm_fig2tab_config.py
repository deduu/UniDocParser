import torch
from transformers import Qwen2_5_VLForConditionalGeneration, Qwen2_5_VLProcessor, BitsAndBytesConfig
from qwen_vl_utils import process_vision_info
from langchain.prompts import ChatPromptTemplate
from backend.core.prompt_config import Fig2Text_Prompt

# Create a prompt instance
prompt = Fig2Text_Prompt()

# VLM Fig2Tab class
class FT_Fig2Tab_PIPELINE:
    def __init__(
        self,
        model_id="Qwen/Qwen2.5-VL-7B-Instruct",
        adapter_path="ZeArkh/Qwen2.5-VL-7B-Instruct-Extract-Figure",
        device="cuda:2" if torch.cuda.is_available() else "cpu",
    ):
        self.model = Qwen2_5_VLForConditionalGeneration.from_pretrained(
            model_id,
            device_map=device,
            torch_dtype=torch.bfloat16,
        )
        self.model.load_adapter(adapter_path)
        self.processor = Qwen2_5_VLProcessor.from_pretrained(model_id)

    def generate(self, image):
        """
        Process a list of images and return the results.
        """
        messages = [
            {
                "role": "system",
                "content": [
                    {"type": "text", "text": prompt.get_system_prompt()},
                ]
            },
            {
                "role": "user",
                "content": [
                    {"type": "image", "image": image},
                    {"type": "text", "text": prompt.get_prompt()},
                ]
            }
        ]

        text_input = self.processor.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )

        image_inputs, _ = process_vision_info(image)

        model_inputs = self.processor(
            text=[text_input],
            images=image_inputs,
            return_tensors="pt",
        ).to(self.model.device)

        generated_ids = self.model.generate(
            **model_inputs, 
            max_new_tokens=4096
        )

        trimmed_generated_ids = [
            out_ids[len(in_ids):] for in_ids, out_ids in zip(model_inputs.input_ids, generated_ids)
        ]

        output_text = self.processor.batch_decode(
            trimmed_generated_ids,
            skip_special_tokens=True,
            clean_up_tokenization_spaces=False
        )

        return output_text[0]
    
fig2tab_vlm = FT_Fig2Tab_PIPELINE()
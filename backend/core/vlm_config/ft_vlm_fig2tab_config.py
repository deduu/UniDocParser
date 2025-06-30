import torch
from unsloth import FastVisionModel
from backend.core.vlm_config.prompt_config import Fig2Text_Prompt
from PIL import Image

fine_tuned_model_list = [
    # Gemma 3
    "ZeArkh/gemma-3-4b-it-Extract-Figure",

    # Llama 3.2
    "ZeArkh/Llama-3.2-11B-Vision-Instruct-Extract-Figure",

    # Qwen 2.5 VL
    "ZeArkh/Qwen2.5-VL-7B-Instruct-unsloth-Extract-Figure",
    "ZeArkh/Qwen2.5-VL-7B-Instruct-bnb-4bit-unsloth-Extract-Figure",
]

# Create a prompt instance
prompt = Fig2Text_Prompt()

# VLM Fig2Tab class
class FT_VLM_Fig2Tab_PIPELINE:
    def __init__(
        self,
        model_id="ZeArkh/Qwen2.5-VL-7B-Instruct-unsloth-Extract-Figure",
        device="cuda" if torch.cuda.is_available() else "cpu",
        temperature=1.5,
        top_p=0.5,
        min_p=0.1,
        max_new_tokens=4096,
    ):
        self.device = device
        self.model, self.processor = FastVisionModel.from_pretrained(
            model_name=model_id,
            load_in_4bit=True if "4bit" in model_id else False,
            device_map=self.device,
        )
        FastVisionModel.for_inference(self.model)  # Enable for inference!
        self.temperature = temperature
        self.top_p = top_p
        self.min_p = min_p
        self.max_new_tokens = max_new_tokens

    def generate(self, image):
        """
        Process a list of images and return the results.
        """
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "image"},
                    {"type": "text", "text": prompt.get_prompt()},
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
            max_new_tokens = self.max_new_tokens,
            use_cache = True, 
            temperature = self.temperature, 
            # top_p = self.top_p,
            min_p = self.min_p
        )

        trimmed_generated_ids = [
            out_ids[len(in_ids):] for in_ids, out_ids in zip(inputs.input_ids, generated_ids)
        ]

        output_text = self.processor.batch_decode(
            trimmed_generated_ids,
            skip_special_tokens=True,
            clean_up_tokenization_spaces=False
        )

        len_output = len(trimmed_generated_ids[0])
        if len_output >= self.max_new_tokens - 1:
            status = "Failed"
        else:
            status = "Success"

        return output_text[0], status
    
# fig2tab_vlm = FT_Fig2Tab_PIPELINE()
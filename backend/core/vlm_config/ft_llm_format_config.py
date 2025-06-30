import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from backend.core.vlm_config.prompt_config import Formatter_Prompt
from peft import PeftModel, LoraConfig, TaskType

# Create a prompt instance
prompt = Formatter_Prompt()

# VLM Formatter class
class FT_LLM_Formatter_PIPELINE:
    def __init__(
        self,
        model_id="Qwen/Qwen2.5-3B-Instruct",
        qwen_ckpt = "backend/weights/qwen2.5_3b-ckpt-2450",
        device="cuda:4",
    ):
        self.model = AutoModelForCausalLM.from_pretrained(
            model_id,
        ).to(device).eval()  # Load the model and set it to evaluation mode.
        if qwen_ckpt:
            config = LoraConfig(
                task_type=TaskType.CAUSAL_LM,  # Specify the task type as causal language modeling.
                target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],  # Target specific layers for LoRA adaptation.
                inference_mode=False,  # Set to False for training mode.
                r=8,  # Rank of the low-rank matrices.
                lora_alpha=32,  # Scaling factor for the low-rank matrices.
                lora_dropout=0.1,  # Dropout rate for LoRA layers.
            )
            self.model = PeftModel.from_pretrained(self.model, model_id=qwen_ckpt, config=config)
        self.tokenizer = AutoTokenizer.from_pretrained(model_id)

    def generate(self, extracted_text: str):
        """
        Process a list of images and return the results.
        """
        messages = [
            {
                "role": "system",
                "content": prompt.get_llm_system_prompt(),
            },
            {
                "role": "user",
                "content": prompt.get_llm_prompt(extracted_text),
            }
        ]

        text_input = self.tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )

        input = self.tokenizer(text_input, return_tensors="pt").to(self.model.device)

        outputs = self.model.generate(
            input.input_ids,
            max_new_tokens=4096
        )

        generated_ids = [
            output_ids[len(input_ids):] for input_ids, output_ids in zip(input.input_ids, outputs)
        ]

        response = self.tokenizer.batch_decode(generated_ids, skip_special_tokens=True)

        return response[0]
    
# formatter_llm = FT_Formatter_PIPELINE()
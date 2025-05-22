import ollama

# Ollama VLM Inference class
class VLM_Ollama:
    def __init__(
        self,
        model_id="qwen2.5vl:7b-q8_0",
        temperature=0.0001,
        top_p=0.95,
        num_ctx=8192,
        max_new_tokens=4096,
    ):
        self.model_id = model_id
        self.temperature = temperature
        self.top_p = top_p
        self.num_ctx = num_ctx
        self.max_new_tokens = max_new_tokens

    def generate(
        self, 
        image_path: str,
        system_prompt: str = "You are a helpful assistant.",
        prompt: str = "Transform the extracted text and structured data from a page into Markdown format based on the image."
    ):
        """
        Process a list of images and return the results.
        """
        with open(image_path, 'rb') as file:
            response = ollama.chat(
                model=self.model_id,
                messages=[
                {
                    'role': 'system',
                        'content': system_prompt
                },
                {
                        'role': 'user',
                        'content': prompt,
                        'images': [file.read()]
                }
                ],
                options={
                    'temperature': self.temperature,
                    'top_p': self.top_p,
                    'num_ctx': self.num_ctx,
                    'max_new_tokens': self.max_new_tokens
                }
            )
        return response['message']['content']
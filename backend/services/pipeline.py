import os
import json
import time
from backend.services.file_handler import split_pdf
from backend.services.image_extraction import extract_images
from backend.services.element_extraction import extract_elements

class PDFExtractionPipeline:
    def __init__(self, pdf_path: str):
        self.pdf_path = pdf_path
        self.pages = []

    def process(self):

        start_time = time.time()

        # Split the PDF into pages and save page images
        self.pages = split_pdf(self.pdf_path)
        print(f"pages: {self.pages}")

        # Extract figures and enrich with metadata using deep learning models
        self.pages = extract_images(self.pages)
        # Extract textual elements and replace figures with table data where applicable
        self.pages = extract_elements(self.pdf_path, self.pages)

        end_time = time.time()
        processing_time = end_time - start_time  # time in seconds
        return {
            "source": os.path.basename(self.pdf_path),
            "pages": self.pages,
            "processing_time": processing_time
        }
    def save_results(self, unique_filename: str, output_dir: str):
        os.makedirs(output_dir, exist_ok=True)
        json_output_path = os.path.join(output_dir, f"{unique_filename}.jsonl")
        md_output_path = os.path.join(output_dir, f"{unique_filename}.md")
        
        # Prepare the extraction result
        extraction_result = {
            "source": os.path.basename(self.pdf_path),
            "pages": self.pages,
            "processing_time": None  # you could include this if needed
        }
        
        # Remove non-serializable items (e.g., the PIL image) from figures
        for page in extraction_result["pages"]:
            if "figures" in page:
                for fig in page["figures"]:
                    if "pil_image" in fig:
                        del fig["pil_image"]
        
        with open(json_output_path, "w") as f:
            json.dump(extraction_result, f, indent=4)
        
        with open(md_output_path, "w") as f:
            for page in extraction_result["pages"]:
                f.write(page["text"])
                f.write("\n\n---\n\n")
        
        return os.path.basename(json_output_path), os.path.basename(md_output_path)


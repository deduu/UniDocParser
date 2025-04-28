import os
import json
import time
from backend.services.file_handler import split_pdf
from backend.services.image_extractor import extract_figures, extract_images
from backend.services.element_extractor import extract_elements
from backend.services.output_formatter import format_extracted_text, format_markdown

class PDFExtractionPipeline:
    def __init__(self, pdf_path: str):
        self.pdf_path = pdf_path
        self.pages = []
        self.figure_list = []

    def process(self):

        start_time = time.time()

        # Split the PDF into pages and save page images
        self.pages = split_pdf(self.pdf_path)
        print(f"pages: {self.pages}")

        # Extract figures using YOLO model
        self.pages = extract_figures(self.pages)

        # Extract textual elements and replace figures with table data where applicable
        self.pages, self.figure_list = extract_elements(self.pages)

        # Extract figures and enrich with metadata using deep learning models
        self.pages = extract_images(self.pages, self.figure_list)

        # Format the extracted text and images
        self.pages = format_extracted_text(self.pages)

        # Format the extracted text into Markdown
        self.pages = format_markdown(self.pages)

        end_time = time.time()
        processing_time = end_time - start_time  # time in seconds
        return {
            "source": os.path.basename(self.pdf_path),
            "pages": self.pages,
            "processing_time": processing_time
        }
    
    def save_results(self, unique_filename: str, output_dir: str):
        os.makedirs(output_dir, exist_ok=True)
        text_output_path = os.path.join(output_dir, f"{unique_filename}.txt")
        json_output_path = os.path.join(output_dir, f"{unique_filename}.jsonl")
        md_output_path = os.path.join(output_dir, f"{unique_filename}.md")
        
        # Prepare the extraction result
        extraction_result = {
            "source": os.path.basename(self.pdf_path),
            "pages": [],
            "processing_time": None  # you could include this if needed
        }
        
        # Remove non-serializable items (e.g., the PIL image) from figures
        for i, page in enumerate(extraction_result["pages"]):
            page_data = {
                "index": i,
                "markdown": page["markdown"],
                "text": page["text"],
                "elements": []
            }
            
            # Process Elements
            for j, el in enumerate(page["elements"]):
                if el["type"] == "image":
                    page_data["elements"].append({
                        "index": j,
                        "type": "image",
                        "bbox": el["bbox"],
                        "text": el["text"],
                        "image_metadata": [{
                            "image_type": el["image_type"],
                            "caption": el["caption"],
                            "description": el["description"],
                            "ocr_string": el["ocr_string"],
                            "image_path": el["image_path"],
                            "image_base64": el["image_base64"],
                        }],
                    })
                else:
                    page_data["elements"].append({
                        "index": i,
                        "type": el["type"],
                        "bbox": el["bbox"],
                        "text": el["text"],
                    })
            
            extraction_result["pages"].append(page_data)
        
        with open(text_output_path, "w") as f:
            for page in extraction_result["pages"]:
                f.write(page["text"])
                f.write("\n\n---\n\n")
        
        with open(json_output_path, "w") as f:
            json.dump(extraction_result, f, indent=4)
        
        with open(md_output_path, "w") as f:
            for page in extraction_result["pages"]:
                f.write(page["text"])
                f.write("\n\n---\n\n")
        
        return os.path.basename(json_output_path), os.path.basename(md_output_path)


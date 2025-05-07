# services/pdf_extractor.py
import os
import json
from typing import List, Dict

class PDFExtractor:
    @staticmethod
    def extract_pdf(pdf_path: str) -> Dict:
        """
        Orchestrate PDF extraction process
        
        Args:
            pdf_path (str): Path to the PDF file
        
        Returns:
            Dict: Extracted PDF content
        """
        from .file_handler import split_pdf
        from .image_extractor import extract_figures, extract_images
        from .element_extractor import extract_elements
        from .output_formatter import format_extracted_text, format_markdown_batch, format_markdown
        
        # Initialize extraction result
        output_metadata = {
            "source": os.path.basename(pdf_path),
            "pages": []
        }
        
        pages = []
        # Split PDF into pages
        pages = split_pdf(pdf_path, pages)
        
        # Extract figures with YOLO
        # pages = extract_figures(pages)
        
        # Extract elements
        pages, figure_list = extract_elements(pages)

        # Extract structured data from image elements
        pages = extract_images(pages, figure_list)

        # Format extracted text and images
        pages = format_extracted_text(pages)

        # Format extracted text into Markdown
        pages = format_markdown(pages)

        # Process pages
        for i, page in enumerate(pages):
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
            
            output_metadata["pages"].append(page_data)
        
        return output_metadata
    
    @staticmethod
    def save_extraction_results(extraction_result: Dict, output_path: str):
        """
        Save extraction results to JSON and Markdown files
        
        Args:
            extraction_result (Dict): Extracted PDF content
            output_path (str): Base path for output files
        """
        # Save text output
        text_output_path = f"{output_path}.txt"
        with open(text_output_path, "w") as f:
            for page in extraction_result["pages"]:
                f.write(page["text"])
                f.write("\n\n---\n\n")

        # Save JSON output
        json_output_path = f"{output_path}.jsonl"
        with open(json_output_path, "w") as f:
            json.dump(extraction_result, f, indent=4)
        
        # Save Markdown output
        md_output_path = f"{output_path}.md"
        with open(md_output_path, "w") as f:
            for page in extraction_result["pages"]:
                f.write(page["markdown"])
                f.write("\n\n---\n\n")
        
        return json_output_path, md_output_path
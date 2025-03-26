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
        from .image_extraction import extract_images
        from .element_extraction import extract_elements
        
        # Initialize extraction result
        pipeline_2 = {
            "source": os.path.basename(pdf_path),
            "pages": []
        }
        
        pages = []
        # Split PDF into pages
        pages = split_pdf(pdf_path, pages)
        
        # Extract images
        pages = extract_images(pages)
        
        # Extract elements
        pages = extract_elements(pdf_path, pages)
        
        # Process pages
        for i, page in enumerate(pages):
            page_data = {
                "index": i,
                "text": page["text"],
                "images": []
            }
            
            # Process images
            for fig in page.get("figures", []):
                page_data["images"].append({
                    "index": os.path.basename(fig.get("file_path", "")),
                    "bbox": fig.get("bbox", []),
                    "name": fig.get("name", ""),
                    "type": fig.get("type", ""),
                    "data": fig.get("data", ""),
                    "description": fig.get("description", "")
                })
            
            pipeline_2["pages"].append(page_data)
        
        return pipeline_2
    
    @staticmethod
    def save_extraction_results(extraction_result: Dict, output_path: str):
        """
        Save extraction results to JSON and Markdown files
        
        Args:
            extraction_result (Dict): Extracted PDF content
            output_path (str): Base path for output files
        """
        # Save JSON output
        json_output_path = f"{output_path}.jsonl"
        with open(json_output_path, "w") as f:
            json.dump(extraction_result, f, indent=4)
        
        # Save Markdown output
        md_output_path = f"{output_path}.md"
        with open(md_output_path, "w") as f:
            for page in extraction_result["pages"]:
                f.write(page["text"])
                f.write("\n\n---\n\n")
        
        return json_output_path, md_output_path
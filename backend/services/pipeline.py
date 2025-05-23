import os
import json
import time
import datetime
from backend.services.file_handler import handle_file, ocr_pdf_to_pdf
from backend.services.image_extractor import extract_images
from backend.services.element_extractor import extract_elements
from backend.services.output_formatter import format_extracted_text, format_markdown

class PDFExtractionPipeline:
    def __init__(self, pdf_path: str):
        self.pdf_path = pdf_path
        self.pages = []
        self.figure_list = []
    
    def ocr_pdf(self, output_dir: str):
        """
        Perform OCR on the PDF file and save the output in a specified directory.
        """
        # Ensure the output directory exists
        os.makedirs(output_dir, exist_ok=True)
        
        # Perform OCR on the PDF
        ocr_pdf_path = ocr_pdf_to_pdf(self.pdf_path, output_dir)
        
        print(f"OCR PDF saved at: {ocr_pdf_path}")
        
        return ocr_pdf_path
        
    def process(self):

        pdf_name = os.path.basename(self.pdf_path)
        start_total_time = time.time()

        # Split the PDF into pages and save page images
        start_file_handling_time = time.time()
        self.pages = handle_file(self.pdf_path)
        end_file_handling_time = time.time()
        print(f"{pdf_name} num of pages: {len(self.pages)}")
        handling_time = end_file_handling_time - start_file_handling_time  # time in seconds
        print(f"{pdf_name} file handled, time:", datetime.timedelta(seconds=handling_time))

        # Extract textual elements and replace figures with table data where applicable
        start_extract_elements_time = time.time()
        self.pages, self.figure_list = extract_elements(self.pages)
        end_extract_elements_time = time.time()
        extract_elements_time = end_extract_elements_time - start_extract_elements_time  # time in seconds
        print(f"{pdf_name} elements extracted, time:", datetime.timedelta(seconds=extract_elements_time))

        # Extract figures and enrich with metadata using deep learning models
        start_extract_figures_time = time.time()
        self.pages = extract_images(self.pages, self.figure_list)
        end_extract_figures_time = time.time()
        extract_figures_time = end_extract_figures_time - start_extract_figures_time  # time in seconds
        print(f"{pdf_name} figures processed, time:", datetime.timedelta(seconds=extract_figures_time))

        # Format the extracted text and images
        start_combining_time = time.time()
        self.pages = format_extracted_text(self.pages)
        end_combining_time = time.time()
        combining_time = end_combining_time - start_combining_time  # time in seconds
        print(f"{pdf_name} elements formatted, time:", datetime.timedelta(seconds=combining_time))

        # Format the extracted text into Markdown
        start_markdown_time = time.time()
        self.pages = format_markdown(self.pages, pdf_name)
        end_markdown_time = time.time()
        markdown_time = end_markdown_time - start_markdown_time  # time in seconds
        print(f"{pdf_name} markdown formatted, time:", datetime.timedelta(seconds=markdown_time))
        
        end_total_time = time.time()
        processing_time = end_total_time - start_total_time  # time in seconds
        print(f"{pdf_name} Total Processing Time:", datetime.timedelta(seconds=processing_time))
        
        clean_source = os.path.basename(self.pdf_path).split("_", 1)[1]
        print(f"Source: {clean_source}")
        
        return {
            "source": clean_source,
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
        
        with open(json_output_path, "w") as f:
            json.dump(extraction_result, f, indent=4)
        
        with open(md_output_path, "w") as f:
            for page in extraction_result["pages"]:
                f.write(page["markdown"])
                f.write("\n\n---\n\n")
        
        return os.path.basename(json_output_path), os.path.basename(md_output_path)


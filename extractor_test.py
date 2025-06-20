# services/pdf_extractor.py
import os
import json
from typing import List, Dict
import time
import datetime

class PDFExtractor:
    @staticmethod
    def extract_pdf_image(pdf_path: str) -> Dict:
        """
        Orchestrate PDF extraction process
        
        Args:
            pdf_path (str): Path to the PDF file
        
        Returns:
            Dict: Extracted PDF content
        """

        from backend.services.file_handler import handle_file
        from backend.services.image_extractor import extract_images
        from backend.services.element_extractor import extract_elements
        from backend.services.output_formatter import format_extracted_text, format_markdown

        pages = []
        figure_list = []
        
        pdf_name = os.path.basename(pdf_path)
        start_total_time = time.time()

        # Split the PDF into pages and save page images
        start_file_handling_time = time.time()
        pages = handle_file(pdf_path)
        end_file_handling_time = time.time()
        print(f"{pdf_name} num of pages: {len(pages)}")
        handling_time = end_file_handling_time - start_file_handling_time  # time in seconds
        print(f"{pdf_name} file handled, time:", datetime.timedelta(seconds=handling_time))

        # Extract textual elements and replace figures with table data where applicable
        start_extract_elements_time = time.time()
        pages, figure_list = extract_elements(pages, pdf_path)
        end_extract_elements_time = time.time()
        extract_elements_time = end_extract_elements_time - start_extract_elements_time  # time in seconds
        print(f"{pdf_name} elements extracted, time:", datetime.timedelta(seconds=extract_elements_time))

        # Extract figures and enrich with metadata using deep learning models
        start_extract_figures_time = time.time()
        pages = extract_images(pages, figure_list)
        end_extract_figures_time = time.time()
        extract_figures_time = end_extract_figures_time - start_extract_figures_time  # time in seconds
        print(f"{pdf_name} figures processed, time:", datetime.timedelta(seconds=extract_figures_time))

        # Format the extracted text and images
        start_combining_time = time.time()
        pages = format_extracted_text(pages)
        end_combining_time = time.time()
        combining_time = end_combining_time - start_combining_time  # time in seconds
        print(f"{pdf_name} elements formatted, time:", datetime.timedelta(seconds=combining_time))

        # Format the extracted text into Markdown
        start_markdown_time = time.time()
        pages = format_markdown(pages, pdf_name)
        end_markdown_time = time.time()
        markdown_time = end_markdown_time - start_markdown_time  # time in seconds
        print(f"{pdf_name} markdown formatted, time:", datetime.timedelta(seconds=markdown_time))
        
        end_total_time = time.time()
        processing_time = end_total_time - start_total_time  # time in seconds
        print(f"{pdf_name} Total Processing Time:", datetime.timedelta(seconds=processing_time))
        
        # clean_source = os.path.basename(pdf_path).split("_", 1)[1]
        # print(f"Source: {clean_source}")
        
        return {
            "source": pdf_path,
            "pages": pages,
            "processing_time": processing_time
        }
    
    @staticmethod
    def extract_excel(file_path: str) -> Dict:
        """
        Extract elements from an Excel file
        
        Args:
            file_path (str): Path to the Excel file
        
        Returns:
            Dict: Extracted Excel content
        """
        from backend.services.file_handler import handle_file
        from backend.services.element_extractor import extract_elements
        from backend.services.output_formatter import format_extracted_text
        from backend.services.image_extractor import extract_images


        pages = []
        figure_list = []
        
        excel_name = os.path.basename(file_path)
        start_total_time = time.time()

        # Split the PDF into pages and save page images
        start_file_handling_time = time.time()
        pages = handle_file(file_path)
        end_file_handling_time = time.time()
        print(f"{excel_name} num of pages: {len(pages)}")
        handling_time = end_file_handling_time - start_file_handling_time  # time in seconds
        print(f"{excel_name} file handled, time:", datetime.timedelta(seconds=handling_time))
        
        # Extract textual elements and replace figures with table data where applicable
        start_extract_elements_time = time.time()
        pages, figure_list = extract_elements(pages, file_path=file_path)
        end_extract_elements_time = time.time()
        extract_elements_time = end_extract_elements_time - start_extract_elements_time  # time in seconds
        print(f"{excel_name} elements extracted, time:", datetime.timedelta(seconds=extract_elements_time))

        # Extract figures and enrich with metadata using deep learning models
        start_extract_figures_time = time.time()
        pages = extract_images(pages, figure_list)
        end_extract_figures_time = time.time()
        extract_figures_time = end_extract_figures_time - start_extract_figures_time  # time in seconds
        print(f"{excel_name} figures processed, time:", datetime.timedelta(seconds=extract_figures_time))

        # Format the extracted text and images
        start_combining_time = time.time()
        pages = format_extracted_text(pages)
        end_combining_time = time.time()
        combining_time = end_combining_time - start_combining_time  # time in seconds
        print(f"{excel_name} elements formatted, time:", datetime.timedelta(seconds=combining_time))

        end_total_time = time.time()
        processing_time = end_total_time - start_total_time  # time in seconds
        print(f"{excel_name} Total Processing Time:", datetime.timedelta(seconds=processing_time))
        
        return {
            "source": file_path,
            "pages": pages,
            "processing_time": processing_time
        }
        
    @staticmethod
    def ocr_pdf_to_pdf(pdf_path: str, output_dir: str) -> str:
        """
        Perform OCR on the PDF and save the output
        
        Args:
            pdf_path (str): Path to the input PDF file
            output_dir (str): Directory to save the OCR processed PDF
        
        Returns:
            str: Path to the OCR processed PDF
        """
        from backend.services.file_handler import ocr_pdf_to_pdf
        
        ocr_pdf_path = ocr_pdf_to_pdf(pdf_path, output_dir)
        
        return ocr_pdf_path
    
    @staticmethod
    def save_extraction_results(extraction_result: Dict):
        """
        Save extraction results to JSON and Markdown files
        
        Args:
            extraction_result (Dict): Extracted PDF content
            output_path (str): Base path for output files
        """
        filename = extraction_result["source"]
        output_path = os.path.join('outputs', os.path.splitext(os.path.basename(filename))[0])

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
    
extarctor = PDFExtractor()

# # Example usage of the PDFExtractor class

# excel_results = extarctor.extract_excel(file_path="/home/dedya/mk.arif/UniDocParser/Simple personal cash flow statement.xlsx")
# json_output_path, md_output_path = extarctor.save_extraction_results(excel_results)
# print(f"\nExcel extraction results: \n{excel_results['pages'][3]['text']}")
# print(f"JSON output saved to: {json_output_path}")
# print(f"Markdown output saved to: {md_output_path}")

pdf_results = extarctor.extract_pdf_image(pdf_path="/home/dedya/mk.arif/UniDocParser/dummy-data.pdf")
json_output_path, md_output_path = extarctor.save_extraction_results(pdf_results)
print(f"\nPDF extraction results saved to: {json_output_path} and {md_output_path}")

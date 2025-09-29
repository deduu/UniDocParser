# save this as split_pdf.py
import sys
from PyPDF2 import PdfReader, PdfWriter


def split_pdf(input_file, page_number, single_page_file, rest_file):
    """
    Splits a PDF into one file containing the selected page and another containing the rest.

    Args:
        input_file (str): Path to input PDF file.
        page_number (int): Page number to separate (1-indexed).
        single_page_file (str): Path to output PDF containing just that page.
        rest_file (str): Path to output PDF containing all other pages.
    """
    reader = PdfReader(input_file)
    single_writer = PdfWriter()
    rest_writer = PdfWriter()

    # Adjust for 0-indexing in PyPDF2
    target_index = page_number - 1

    for i, page in enumerate(reader.pages):
        if i == target_index:
            single_writer.add_page(page)
        else:
            rest_writer.add_page(page)

    # Write files
    with open(single_page_file, "wb") as f:
        single_writer.write(f)

    with open(rest_file, "wb") as f:
        rest_writer.write(f)

    print(f"✅ Page {page_number} saved to {single_page_file}")
    print(f"✅ Remaining pages saved to {rest_file}")


if __name__ == "__main__":
    if len(sys.argv) != 5:
        print("Usage: python split_pdf.py <input.pdf> <page_number> <page.pdf> <rest.pdf>")
        sys.exit(1)

    input_pdf = sys.argv[1]
    page_num = int(sys.argv[2])
    single_page_output = sys.argv[3]
    rest_output = sys.argv[4]

    split_pdf(input_pdf, page_num, single_page_output, rest_output)

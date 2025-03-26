from unstructured.partition.pdf import partition_pdf
import markdownify
import re

# Function to extract elements from PDF
def element_extractor(pdf_path):
    # Partitioning file
    raw_pdf_elements = partition_pdf(
        filename=pdf_path,
        extract_images_in_pdf=True,
        infer_table_structure=True,
    )

    # split raw_pdf_elements per page_number
    element_pages = []

    for element in raw_pdf_elements:
        page_number = element.metadata.page_number
        if len(element_pages) < page_number:
            element_pages.append([])
        element_pages[page_number - 1].append(element)

    return element_pages

# Post-process extracted elements
import markdownify

# Process the extracted string
def process_string(string):
    # lowercase the string
    string = string.lower()
    # remove punctuation
    string = re.sub(r'[^\w\s]', '', string)
    # remove extra whitespaces
    string = re.sub(r'\s+', '', string)
    return string

# Extract elements to text and replace figures with tables
def extract_elements_to_text(elements, figures):
    figures = figures.copy()
    string: list[str] = []

    for i, element in enumerate(elements):
        if "unstructured.documents.elements.Table" in str(type(element)):
            table = markdownify.markdownify(element.metadata.text_as_html)
            string.append(table)
        elif "unstructured.documents.elements.Image" in str(type(element)):
            name_dist = []
            # count the distance between the image and the figure
            for fig in figures:
                count = 0
                fig_name = fig['name']
                for j in range(i, len(elements)):
                    if process_string(fig_name) in process_string(str(elements[j])):
                        name_dist.append(count)
                        break
                    count += 1
            # get the closest figure
            if len(name_dist) > 0:
                min_dist = min(name_dist)
                fig = figures[name_dist.index(min_dist)]
                string.append(fig["data"])
                figures.remove(fig)
        else:
            string.append(markdownify.markdownify(str(element), heading_style="ATX"))

    if len(figures) > 0:
        for fig in figures:
            string.append(fig["name"])
            string.append(fig["data"])

    return "\n\n".join(string)

# Extract elements from PDF
def extract_elements(pdf_path, pages):
    elements = element_extractor(pdf_path)
    print("Number of extracted elements:", len(elements))
    print("Number of pages:", len(pages))
    for i, page in enumerate(pages):
        if i < len(elements):
            page["text"] = extract_elements_to_text(elements[i], page["figures"])
        else:
            # Handle missing elements appropriately
            page["text"] = ""
            print(f"Warning: No elements found for page index {i}")
    return pages

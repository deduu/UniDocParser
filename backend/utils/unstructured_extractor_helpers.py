import re

# Unstructured Document Helper Functions
## Unstructured Document Page Splitter
def split_elements(elements: list):
    """
    Splits elements into pages based on their metadata.
    Args:
        elements (list): List of elements extracted from a document.
    Returns:
        list: List of lists, where each sublist contains elements for a specific page.
    """
    elements_per_page = []

    for element in elements:
        page_number = element.metadata.page_number - 1  # Adjusting to zero-based index
        if len(elements_per_page) <= page_number:
            elements_per_page.append([])

        elements_per_page[page_number].append(element)

    return elements_per_page

## Function to extract bounding box coordinates from the element.
def extract_bbox(points):
    x_coords = [point[0] for point in points]
    y_coords = [point[1] for point in points]

    return [min(x_coords), min(y_coords), max(x_coords), max(y_coords)]

# Unstructured Table Helper Functions
## Clean markdown table function
def filter_table(md_table):
    lines = md_table.split('\n')
    cleaned_lines = []
    for line in lines:
        # if line only contains |  |  | ... | or | --- | --- | --- | --- | ... | or is empty, skip it
        if re.match(r'^\|(\s*\|)+\s*$', line) or re.match(r'^\|(\s*---\s*\|)+\s*$', line) or not line.strip():
            continue
        # remove leading and trailing whitespace
        line = line.strip()
        cleaned_lines.append(line)
        
    return '\n'.join(cleaned_lines)

## Function to get the number of columns in a Markdown table
def get_len_columns(md_table):
    lines = md_table.split('\n')
    # remove line with len 0
    lines = [line for line in lines if line.strip()]
    if len(lines) > 0:
        first_line = lines[0]
        num_pipes = first_line.count('|')
        return num_pipes
    return 0

## Function to format a Markdown table by adding a separator line
def format_table(md_table):
    lines = md_table.split('\n')
    # count | in the first line
    num_pipes = get_len_columns(md_table)
    if num_pipes > 0:
        second_line = '|' + '|'.join([' --- '] * (num_pipes - 1)) + '|'
        lines.insert(1, second_line)
    return '\n'.join(lines)
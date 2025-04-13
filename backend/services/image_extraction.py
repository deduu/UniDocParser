import cv2
import os
import supervision as sv
from PIL import Image
from backend.services.model_manager import YOLO_MODEL, VLM_PIPELINE

# Extract figures from pages using the preloaded YOLO model
import cv2
import os
import supervision as sv
from PIL import Image
from backend.services.model_manager import YOLO_MODEL

def extract_figures(pages):
    for j, page in enumerate(pages):
        image = cv2.imread(page['image'])  # BGR
        results = YOLO_MODEL(image, conf=0.35, iou=0.7)[0]
        detections = sv.Detections.from_ultralytics(results)

        for i, class_name in enumerate(detections.data['class_name']):
            if class_name == 'figure':
                x1, y1, x2, y2 = map(int, detections.xyxy[i])
                # Crop the figure from the original BGR image
                section = image[y1:y2, x1:x2]

                # Convert BGR cropped image to RGB for PIL
                section_rgb = cv2.cvtColor(section, cv2.COLOR_BGR2RGB)
                pil_image = Image.fromarray(section_rgb)

                # Save to disk for cross-checking
                output_filename = os.path.join(
                    "backend", "img", "figures", f"page_{j}_figure_{i}.png"
                )
                cv2.imwrite(output_filename, section)  # Writes the BGR image

                # Store both the in-memory PIL image and the file path
                metadata = {
                    "file_path": output_filename,
                    "bbox": [x1, y1, x2, y2],
                    "name": "",
                    "type": "",
                    "data": "",
                    "description": "",
                    "pil_image": pil_image,  # in-memory version for immediate usage
                }
                page["figures"].append(metadata)
            # check duplicate figures by bounding box
    for i, page in enumerate(pages):
        figures = page['figures']
        for j in range(len(figures)):
            for k in range(j + 1, len(figures)):
                if figures[j]['bbox'] == figures[k]['bbox']:
                    # remove duplicate figure
                    del figures[k]
                    break
    return pages


# Figure to Table VLM
SYSTEM_FIGURE_PROMPT = """You are a helpful assistant who helps users convert images into understandable formats. 
First, provide the name of the image that you will receive. Then, determine if the image is a graph/chart or simply another type of image. 
If it is a graph/chart, state the chart type and convert it to structured table data in Markdown format with a short explanation or context analysis. 
If it is not a graph/chart, briefly describe the image's content in natural language using short sentences."""

PROMPT_FIGURE_TEMPLATE = """Convert the provided figure image into an understandable format.
Output format:
1.	Chart/graph:
- Figure Name: …
- Chart Type: …
```data
| Structured Table Data |
```
- Short Description: …

2.	If the image is not a chart:
- Figure Name: …
- Short Description: …
"""

def fig_to_table(pil_image):
    # pil_image is already a PIL image in RGB
    
    messages = [
        {
            "role": "system",
            "content": [
                {"type": "text", "text": SYSTEM_FIGURE_PROMPT}
            ]
        },
        {
            "role": "user",
            "content": [
                {"type": "image", "image": pil_image},  # in-memory PIL image
                {"type": "text", "text": PROMPT_FIGURE_TEMPLATE}
            ]
        }
    ]
    
    output = VLM_PIPELINE(text=messages)

 
    result = output[0]["generated_text"][-1]["content"]
    return result


def take_data(result_text):
    if "```data" not in result_text:
        return take_desc(result_text)
    data_text = result_text.split("```data")[1].strip().split("```")[0].strip()
    return data_text

def take_desc(result_text):
    if "Short Description:" not in result_text:
        return ""
    return result_text.split("Short Description:")[1].strip()

def take_name(result_text):
    if "Figure Name:" not in result_text:
        return ""
    return result_text.split("Figure Name:")[1].strip().split("\n")[0].strip()

def take_type(result_text):
    if "Chart Type:" not in result_text:
        return "image"
    return result_text.split("Chart Type:")[1].strip().split("\n")[0].strip()

def post_process_figures(result):
    name = take_name(result)
    type_ = take_type(result)
    tab = take_data(result)
    desc = take_desc(result)
    return name, type_, tab, desc

def extract_images(pages):
    pages = extract_figures(pages)
    for page in pages:
        for figure in page['figures']:
            fig2table = fig_to_table(figure['pil_image'])
            name, type_, tab, desc = post_process_figures(fig2table)
            figure['name'] = name
            figure['type'] = type_
            figure['data'] = tab
            figure['description'] = desc
    return pages

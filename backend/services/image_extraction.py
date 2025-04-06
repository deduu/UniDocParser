import cv2
import os
import supervision as sv
from PIL import Image
from backend.services.model_manager import YOLO_MODEL, VLM_PIPELINE

# Extract figures from pages using the preloaded YOLO model
def extract_figures(pages):
    for j, page in enumerate(pages):
        image = cv2.imread(page['image'])
        results = YOLO_MODEL(image, conf=0.35, iou=0.7)[0]
        detections = sv.Detections.from_ultralytics(results)
        for i, class_name in enumerate(detections.data['class_name']):
            if class_name == 'figure':
                x1, y1, x2, y2 = map(int, detections.xyxy[i])
                section = image[y1:y2, x1:x2]
                output_filename = os.path.join("backend", "img", "figures", f"page_{j}_figure_{i}.png")
                cv2.imwrite(output_filename, section)
                metadata = {
                    "file_path": output_filename,
                    "bbox": [x1, y1, x2, y2],
                    "name": "",
                    "type": "",
                    "data": "",
                    "description": ""
                }
                page["figures"].append(metadata)
    return pages

# Prompts for VLM processing
SYSTEM_PROMPT = (
    "You are a helpful assistant who helps users convert images into understandable formats. "
    "First, provide the name of the image that you will receive. Then, determine if the image is a graph/chart or simply another type of image. "
    "If it is a graph/chart, state the chart type and convert it to structured table data in Markdown format with a short explanation or context analysis. "
    "If it is not a graph/chart, briefly describe the image's content in natural language using short sentences."
)

PROMPT_TEMPLATE = (
    "Convert the provided figure image into an understandable format.\n"
    "Output format:\n"
    "1.	Chart/graph:\n"
    "- Figure Name: …\n"
    "- Chart Type: …\n"
    "```data\n| Structured Table Data |\n```\n"
    "- Short Description: …\n\n"
    "2.	If the image is not a chart:\n"
    "- Figure Name: …\n"
    "- Short Description: …\n"
)

def fig_to_table(image_path):
    # Load the image using PIL and convert it to RGB
    image = Image.open(image_path).convert("RGB")
    messages = [
        {
            "role": "system",
            "content": [
                {"type": "text", "text": SYSTEM_PROMPT}
            ]
        },
        {
            "role": "user",
            "content": [
                {"type": "image", "image": image},
                {"type": "text", "text": PROMPT_TEMPLATE}
            ]
        }
    ]
    output = VLM_PIPELINE(text=messages, max_new_tokens=200)
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
            fig2table = fig_to_table(figure['file_path'])
            name, type_, tab, desc = post_process_figures(fig2table)
            figure['name'] = name
            figure['type'] = type_
            figure['data'] = tab
            figure['description'] = desc
    return pages

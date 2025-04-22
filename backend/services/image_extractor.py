import cv2
import os
import supervision as sv
from PIL import Image
from backend.services.model_manager import YOLO_MODEL, Fig2Tab_PIPELINE

def extract_figures(pages):
    for j, page in enumerate(pages):
        image = cv2.imread(page['image'])  # BGR
        results = YOLO_MODEL(image, conf=0.35, iou=0.7)[0]
        detections = sv.Detections.from_ultralytics(results)

        if len(detections.data['class_name']) == 0:
            page["yolo_used"] = False
            continue
        elif len(set(detections.data['class_name'])) == 1 and detections.data['class_name'][0] == 'figure':
            page["yolo_used"] = False
            continue
        else:
            # save figure class_name
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
                        "element_index": 9999,
                        "file_path": output_filename,
                        "bbox": [x1, y1, x2, y2],
                        "pil_image": pil_image,  # in-memory version for immediate usage
                    }
                    page["yolo_figures"].append(metadata)

    # check duplicate figures by bounding box
    for i, page in enumerate(pages):
        figures = page['yolo_figures']
        for j in range(len(figures)):
            for k in range(j + 1, len(figures)):
                if figures[j]['bbox'] == figures[k]['bbox']:
                    # remove duplicate figure
                    del figures[k]
                    break
    return pages


# Figure to Table VLM
SYSTEM_FIG_TEMPLATE = """You are a helpful assistant focused on converting images into easily understandable formats. Follow these steps:
Classify the image:
- If the image is a graph/chart, identify the type and convert the data into a structured table in Markdown format, providing a brief context or analysis.
- If the image is a flowchart, convert it into Mermaid code, accompanied by a brief explanation or analysis.
- If the image is not a graph/chart or flowchart, provide a concise description of the image’s content using short sentences.
If the image contains caption or title, include it fully in the output. If not available, leave it blank.
"""

USER_FIG_TEMPLATE = """Convert the provided figure image into an understandable format.

---

Output format if the image a chart/graph:
- Figure Caption: (image caption or title if available, otherwise "image")
- Type: (Bar Chart, Line Graph, Pie Chart, etc.)
data:
| Structured Table Data |
enddata;
- Short Description: …

---

Output format if the image is a flowchart:
- Figure Caption: (image caption or title if available, otherwise "image")
- Type: Flowchart
data:
```mermaid
Mermaid Code
```
enddata;
- Short Description: …

---

Output format if another image:
- Figure Caption: (image caption or title if available, otherwise "image")
- Type: …
- Short Description: …
"""

def fig_to_table(pil_image):
    # pil_image is already a PIL image in RGB
    messages = [
        {
            "role": "system",
            "content": [
                {"type": "text", "text": SYSTEM_FIG_TEMPLATE}
            ]
        },
        {
            "role": "user",
            "content": [
                {"type": "image", "image": pil_image},  # in-memory PIL image
                {"type": "text", "text": USER_FIG_TEMPLATE}
            ]
        }
    ]
    
    output = Fig2Tab_PIPELINE(text=messages)

    result = output[0]["generated_text"][-1]["content"]
    return result


def take_data(result_text):
    data_text = result_text
    # check if the text contains data:
    if "data:" not in data_text:
        return take_desc(result_text)
    # split the text by data:
    data_text = data_text.split("data:")[1].strip()

    if "enddata;" in data_text:
        data_text = data_text.split("enddata;")[0].strip()
    else:
        data_text = data_text.split("Short Description:")[0].strip()

    return data_text

def take_desc(result_text):
    desc_text = result_text
    if "Short Description:" not in desc_text:
        return ""
    desc_text = desc_text.split("Short Description:")[1].strip()
    return desc_text

def take_caption(result_text):
    caption_text = result_text
    if "Figure Caption:" not in caption_text:
        return ""
    caption_text = caption_text.split("Figure Caption:")[1].strip()
    caption_text = caption_text.split("\n")[0].strip()
    return caption_text

def take_type(result_text):
    type_text = result_text
    if "Type:" not in type_text:
        return "image"
    type_text = type_text.split("Type:")[1].strip()
    type_text = type_text.split("\n")[0].strip()
    return type_text.lower()

def post_process_figures(result):
    caption = take_caption(result)
    type_ = take_type(result)
    tab = take_data(result)
    desc = take_desc(result)
    return caption, type_, tab, desc

def extract_images(pages):
    for i, page in enumerate(pages):
        for j, element in enumerate(page['elements']):
            if element['type'] == 'image':
                print(f"Processing Page {i} - Figure {j}")
                result = fig_to_table(element['pil_image'])

                caption, img_type, data, desc = post_process_figures(result)

                # element["type"] = img_type.lower()
                element["text"] = data
                element["caption"] = caption
                element["description"] = desc

    return pages

import cv2
import os
import supervision as sv
from PIL import Image
from backend.services.model_manager import YOLO_MODEL, Fig2Tab_PIPELINE, vlm_tokenizer

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
- If the image is a logo, write the description as the company name without any explanation.
If the image contains caption or title, include it fully in the output. If not available, leave it blank.
"""

PROMPT_FIG_TEMPLATE = """Convert the provided figure image into an understandable format.

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
- Short Description: (Short description of the image, if it is a logo just write the company name)
"""


def fig_to_table(figure_list):
    # image_batchs = [figure_list[i:i + batch_size] for i in range(0, len(figure_list), batch_size)]

    # for i, image_batch in enumerate(image_batchs):
    messages = []
    for i, image in enumerate(figure_list):
        pil_image = image["pil_image"]
        messages.append([
            {
                "role": "system",
                "content": [
                    {"type": "text", "text": SYSTEM_FIG_TEMPLATE}
                ]
            },
            {
                "role": "user",
                "content": [
                    {"type": "image", "image": pil_image},
                    {"type": "text", "text": PROMPT_FIG_TEMPLATE}
                ]
            }
        ])

    output = Fig2Tab_PIPELINE(text=messages)

    results = []
    output_tokens_length = []
    # Exception for reformatting the output
    for i, out in enumerate(output):
        generated_text = out[0]["generated_text"][-1]["content"]
        results.append({
                "page_num": figure_list[i]["page_num"],
                "idx": figure_list[i]["idx"],
                "messages": messages[i],
                "generated_text": generated_text
        })
        output_tokens = vlm_tokenizer(out[0]["generated_text"][-1]["content"], return_tensors="pt").input_ids
        output_tokens_length.append(output_tokens.shape[1])

    do_reformat = True
    while do_reformat:
        reformat_messages = []
        reformat_index = []
        for i, res in enumerate(results):
            if "addCriterion" in res["generated_text"]:
                reformat_messages.append(res["messages"])
                reformat_index.append(i)
                do_reformat = True
        if len(reformat_index) == 0:
            do_reformat = False
            break
        else:
            reformat_output = Fig2Tab_PIPELINE(text=reformat_messages)
            for i, out in enumerate(reformat_output):
                generated_text = out[0]["generated_text"][-1]["content"]
                results[reformat_index[i]]["generated_text"] = generated_text

    for i, fig in enumerate(figure_list):
        for j, res in enumerate(results):
            if fig["page_num"] == res["page_num"] and fig["idx"] == res["idx"]:
                figure_list[i]["generated_text"] = res["generated_text"]
                break

    return figure_list, output_tokens_length


def take_data(result_text):
    data_text = result_text
    if "data:" in data_text:
        # split the text by data:
        data_text = data_text.split("data:")[1].strip()
        if "enddata;" in data_text:
            data_text = data_text.split("enddata;")[0].strip()
        else:
            data_text = data_text.split("Short Description:")[0].strip()
    else:
        return take_desc(result_text)
    
    return data_text

def take_desc(result_text):
    desc_text = result_text
    if "Short Description:" not in desc_text:
        return ""
    desc_text = desc_text.split("Short Description:")[1].strip()
    return desc_text

def take_caption(result_text):
    caption_text = result_text
    # check if the text contains Figure Caption:
    if "Figure Caption:" in caption_text:
        caption_text = caption_text.split("Figure Caption:")[1].strip()
    elif "addCriterion:" in caption_text:
        caption_text = caption_text.split("addCriterion:")[1].strip()
    else:
        return ""
    caption_text = caption_text.split("\n")[0].strip()
    return caption_text

def take_type(result_text):
    type_text = result_text
    if "Type:" not in type_text:
        return "image"
    type_text = type_text.split("Type:")[1].strip()
    type_text = type_text.split("\n")[0].strip()
    return type_text.lower()

def extract_images(pages, figure_list):

    figure_list, output_tokens_length = fig_to_table(figure_list)

    for i, fig in enumerate(figure_list):
        # check if the result is empty
        if fig["generated_text"] == "":
            continue
        
        for el in pages[fig["page_num"]]["elements"]:
            if el["idx"] == fig["idx"]:
                el["text"] = take_data(fig["generated_text"])
                el["description"] = take_desc(fig["generated_text"])
                el["caption"] = take_caption(fig["generated_text"])
                el["image_type"] = take_type(fig["generated_text"])
                break

    return pages, output_tokens_length

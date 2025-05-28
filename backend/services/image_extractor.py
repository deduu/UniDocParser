import cv2
import os
from PIL import Image
import re
from backend.core.vlm_fig2tab_config import fig2tab_vlm

# Figure to Table VLM
def fig_to_table(figure_list):

    images = []
    for i, image in enumerate(figure_list):
        images.append(image["image_path"])

    output = fig2tab_vlm.generate(images)

    # Exception for reformatting the output
    for i, out in enumerate(output):
        figure_list[i]["generated_text"] = out

    return figure_list

def take_data(result_text):
    data_text = result_text
    if "data:" in data_text:
        # split the text by data:
        data_text = data_text.split("data:")[1].strip()
        if "enddata;" in data_text:
            data_text = data_text.split("enddata;")[0].strip()
        else:
            data_text = data_text.split("Concise Description:")[0].strip()
    else:
        return take_desc(result_text)
    
    return data_text

def take_desc(result_text):
    desc_text = result_text
    if "Concise Description:" not in desc_text:
        return ""
    desc_text = desc_text.split("Concise Description:")[1].strip()
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
        return "general image"
    type_text = type_text.split("Type:")[1].strip()
    type_text = type_text.split("\n")[0].strip()
    return type_text.lower()

def extract_images(pages, figure_list):

    figure_list = fig_to_table(figure_list)

    for i, fig in enumerate(figure_list):
        # check if the result is empty
        if fig["generated_text"] == "":
            continue
        
        for el in pages[fig["page_num"]]["elements"]:
            if el["idx"] == fig["idx"]:
                el["text"] = take_data(fig["generated_text"])
                el['image_metadata']["image_type"] = take_type(fig["generated_text"])
                el['image_metadata']["caption"] = take_caption(fig["generated_text"])
                el['image_metadata']["description"] = take_desc(fig["generated_text"])
                break

    return pages

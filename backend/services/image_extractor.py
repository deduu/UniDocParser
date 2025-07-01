def take_data(result_text):
    data_text = result_text
    if "data:" in data_text:
        # split the text by data:
        data_text = data_text.split("data:")[1].strip()
        if "enddata" in data_text:
            data_text = data_text.split("enddata")[0].strip()
    else:
        return take_desc(result_text)
    
    return data_text

def take_desc(result_text):
    desc_text = result_text
    if "Concise Description:" not in desc_text:
        return ""
    desc_text = desc_text.split("Concise Description:")[1].strip()
    desc_text = desc_text.split("\n")[0].strip()
    return desc_text

def take_caption(result_text):
    caption_text = result_text
    # check if the text contains Concise Description:
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

def extract_images(fig2tab_model, pages, figure_list):
    """ 
    Extracts images from the figure list and updates the pages with generated text and metadata.
    Args:
        pages (list): List of pages containing elements.
        figure_list (list): List of figures with PIL images and metadata.
    Returns:
        list: Updated pages with generated text and metadata for each figure.
    """

    for i, image in enumerate(figure_list):

        output, status = fig2tab_model.generate(image["pil_image"])
        figure_list[i]["generated_text"] = output
        figure_list[i]["status"] = status
        print(f"Figure {image['idx']} from page {image['page_num']} processed with status: {status}")
        
        for el in pages[image["page_num"]]["elements"]:
            if el["idx"] == image["idx"]:
                el["status"] = image["status"]
                el["text"] = take_data(image["generated_text"])
                el['image_metadata']["image_type"] = take_type(image["generated_text"])
                el['image_metadata']["caption"] = take_caption(image["generated_text"])
                el['image_metadata']["description"] = take_desc(image["generated_text"])
                break

    return pages, figure_list

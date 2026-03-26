import logging
import time
from PIL import Image, ImageDraw


class ImageType:
    '''
    图片类型常量类
    '''
    PRODUCT = "产品图"
    PACKAGE = "外包装图"
    MANUAL = "说明书"

class ModelType:
    '''
    模型类型常量类
    '''
    GPT_4O = "gpt-4o"
    O4_MINI = "o4-mini"
    O3_MINI = "O3-mini"
    QWEN_VL_MAX = "qwen-vl-max"

class CutType:
    '''
    切割类型常量类
    '''
    PER_BOUNDING_BOX = "per_boundingbox"
    STACK_BOUNDING_BOX = "stack_boundingbox"

class RuleCheckMode:
    '''
    规则检查模型常量类
    '''
    MULTI_IMAGE_VLM = "multi_image_vlm"
    SINGLE_IMAGE_VLM = "single_image_vlm"


def call_openai_llm(model_client, model_name: str, content: str) -> str:
    response = None
    max_retries = 3
    timeout = 90  # 60秒超时
    for attempt in range(max_retries):
        try:    
            if model_name == ModelType.O4_MINI:
                response = model_client.chat.completions.create(
                    model = model_name,
                    temperature = 1,
                    messages=[
                        {
                            "role": "user",
                            "content": content
                        }
                    ],
                    timeout=timeout
                )
            elif model_name in [ModelType.GPT_4O, ModelType.QWEN_VL_MAX]:
                response = model_client.chat.completions.create(
                    model=model_name,
                    temperature=0.1,
                    messages=[
                        {
                            "role": "user",
                            "content": content
                        }
                    ],
                    timeout=timeout
                ) 
            else:
                logging.error(f"model type is not support! {model_name}")
            # 如果成功获取响应，直接返回
            return response
        except Exception as e:
            logging.warning(f"Attempt {attempt + 1}/{max_retries} failed: {str(e)}")
        if attempt == max_retries - 1:
            logging.error(f"All {max_retries} attempts failed for model {model_name}")
            return None
         # 等待一段时间后重试
        time.sleep(2 ** attempt)  # 指数退避
    return response

'''
    多轮对话形式
'''
def call_multi_conservations_openai_llm(model_client, model_name: str, messages: list) -> str:
    response = None
    max_retries = 3
    timeout = 90  # 60秒超时
    
    for attempt in range(max_retries):
        try:
            #logging.info(f"messages: {messages}")
            if model_name == ModelType.O4_MINI:
                response = model_client.chat.completions.create(
                    model=model_name,
                    temperature=1,
                    messages=messages,
                    timeout=timeout
                )
            elif model_name in [ModelType.GPT_4O, ModelType.QWEN_VL_MAX]:
                response = model_client.chat.completions.create(
                    model=model_name,
                    temperature=0.1,
                    messages=messages,
                    timeout=timeout
                ) 
            else:
                logging.error(f"model type is not support! {model_name}")
                return None
            
            # 如果成功获取响应，直接返回
            return response
            
        except Exception as e:
            logging.warning(f"Attempt {attempt + 1}/{max_retries} failed: {str(e)}")
            if attempt == max_retries - 1:
                logging.error(f"All {max_retries} attempts failed for model {model_name}")
                return None
            # 等待一段时间后重试
            time.sleep(2 ** attempt)  # 指数退避
    
    return response


def draw_yolo_boxes(image_path, bounding_boxes, output_path, class_names=None):
    """
    Draw YOLO-format bounding boxes on the image and save.

    Args:
        image_path (str): Path to the image.
        bounding_boxes (list): List of bounding boxes in YOLO format [class_id, x_center, y_center, width, height].
        output_path (str): Path to save the rendered image.
        class_names (list, optional): List of class names for labeling.
    """
    image = Image.open(image_path).convert("RGB")
    draw = ImageDraw.Draw(image)
    w, h = image.size

    for box in bounding_boxes:
        # YOLO format: [class_id, x_center, y_center, width, height] (all normalized 0-1)
        if isinstance(box, dict):
            # Sometimes the box may be a dict
            class_id = box.get("class_id", 0)
            x_center = float(box["x_center"])
            y_center = float(box["y_center"])
            width = float(box["width"])
            height = float(box["height"])
        else:
            # Assume list or tuple
            if len(box) == 5:
                class_id, x_center, y_center, width, height = box
            elif len(box) == 4:
                # No class_id
                class_id = 0
                x_center, y_center, width, height = box
            else:
                continue

        # Convert normalized coordinates to pixel values
        x_center *= w
        y_center *= h
        width *= w
        height *= h

        x1 = int(x_center - width / 2)
        y1 = int(y_center - height / 2)
        x2 = int(x_center + width / 2)
        y2 = int(y_center + height / 2)
        logging.info(f"x1: {x1}, y1: {y1}, x2: {x2}, y2: {y2}, x_center: {x_center}, y_center: {y_center}, width: {width}, height: {height}")
        draw.rectangle([x1, y1, x2, y2], outline="red", width=3)
        if class_names and class_id < len(class_names):
            label = str(class_names[class_id])
        else:
            label = str(class_id)
        draw.text((x1, y1), label, fill="red")

    image.save(output_path)

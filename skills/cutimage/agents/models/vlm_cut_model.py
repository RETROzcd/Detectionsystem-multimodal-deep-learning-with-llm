from agents.image_cut.models.vlm_cut_prompt import IMAGE_CUT_PROMPT
from agents.single_image_vlm_model import SingleImageVlmModel
import logging
import json
import traceback
import os

class VlmCutModel:   
    '''
    基于VLM的切图模型
    '''
    def __init__(self, model_configs):
        self._model_configs = model_configs
        self._single_image_vlm_model = SingleImageVlmModel(model_configs)
        self._cut_image_prompt = IMAGE_CUT_PROMPT[model_configs["prompt_version"]]

    def cut_image(self, image_path: str) -> list[str]:
        upload_status, image_size = self._single_image_vlm_model.upload_image(image_path)
        if upload_status == True:
            qa_status, answer, usage = self._single_image_vlm_model.ask(self._cut_image_prompt)
            if qa_status == True:
                try:
                    logging.info(f"answer: {answer}")
                    result = json.loads(answer.replace("```json", "").replace("```", ""))
                    boundingboxes = result.get("boundingboxes", [])
                    w, h = image_size
                    infer_result = []
                    for box in boundingboxes:
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
                        x1 = max(0, int(x_center - width / 2))
                        y1 = max(0, int(y_center - height / 2))
                        x2 = min(w, int(x_center + width / 2))
                        y2 = min(h, int(y_center + height / 2))
                        infer_result.append((x1, y1, x2 - x1, y2 - y1))
                    return infer_result
                except Exception as e:
                    traceback.print_exc()
                    logging.error(f"failed to parse answer: {e}")
                    return []
            else:
                return []
        else:
            logging.error(f"failed to upload: status: {upload_status}")
            return []

if __name__ == "__main__":
    # 配置日志
    os.makedirs("./logs", exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s',
        handlers=[
            logging.FileHandler("./logs/vlm_cut_model.log"),
            logging.StreamHandler()
        ],
        force=True
    )
    # gpt-4o
    model_configs = {
                "prompt_version": "image_cut_v1",
                "model_name": "gpt-4o",
                "api_key": "b521d39f2a8748b784c254faa568b1ca",
                "api_version": "2025-01-01-preview",
                "azure_endpoint": "https://digitalai-southindia-ai.openai.azure.com"
    }
    #o4-mini
    model_configs = {
        "prompt_version": "image_cut_v1",
        "model_name": "o4-mini",
        "api_key": "66fa2e5566b4474cba373a0b69e98bd3",
        "api_version": "2025-01-01-preview",
        "azure_endpoint": "https://digitalai-eastus2-ai.openai.azure.com",
        "max_image_size": 2048 #-1 #2048
    }

    vlm_cut_model = VlmCutModel(model_configs)
    bounding_boxes = vlm_cut_model.cut_image("./samples/T52510260108TP-高拍仪/产品/20250113133920563.jpg")
    logging.info(f"bounding_boxes: {bounding_boxes}")

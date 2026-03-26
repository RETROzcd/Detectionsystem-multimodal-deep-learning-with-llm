from agents.image_cut.image_cut_request import ImageCutRequest
from agents.image_cut.image_cut_response import ImageCutResponse
from agents.image_cut.image_cut_model import ImageCutModel
from agents.agent_utils import CutType
import logging
import os
class ImageCutAgent:
    def __init__(self, model_configs:dict):
        self.image_cut_model = ImageCutModel(model_configs)
        logging.info(f"ImageCutAgent initialized with model_configs: {model_configs}")
    def cut_images(self, request:ImageCutRequest) -> ImageCutResponse:
        logging.info(f"start to Cutting images with request: {request}")
        response = self.image_cut_model.cut_images(request)
        logging.info(f"end to Cutting images with request: {request} finished, response: {response}")
        return response

if __name__ == "__main__":
    # 配置日志
    os.makedirs("./logs", exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s',
        handlers=[
            logging.FileHandler("./logs/image_cut.log"),
            logging.StreamHandler()
        ],
        force=True
    )

    model_configs = {   
        "sam_model_name": "FastSAM",
        "sam_model_ckpt": "./models/FastSAM-s.pt",
        "sam_device_id": "cpu",
        "sam_max_size": 512,
        "sam_conf": 0.15,
        "sam_iou": 0.5,
        "sam_occupy_ratio": 0.35, # 过滤超过这个占比的框
        "ocr_sam_iou_threshold": 0.1, # iou threshold
        "model_input_image_size": (768, 768), # 下游模型的图片输入大小(height, width)
        "cut_mode": CutType.STACK_BOUNDING_BOX,
        "debug": True, # 是否启动调试模式
        "enable_vlm_cut": True,
        "enable_ocr_cut": False,
        "enable_sam_cut": False,
        "vlm_cut_model_configs": {
            ?
        }
    }
    image_cut_agent = ImageCutAgent(model_configs)
    logging.info(f"request: {request}")
    response = image_cut_agent.cut_images(request)
    logging.info(f"response: {response}")
'''
This agent is responsible for cutting the image.
'''
from agents.image_cut.image_cut_request import ImageCutRequest
from agents.image_cut.image_cut_response import ImageCutResponse
from agents.image_cut.image_cut_model import ImageCutModel
from agents.agent_utils import CutType
import logging
import os


class ImageCutAgent:
    '''
    This agent is responsible for cutting the image.
    '''
    def __init__(self, model_configs:dict):
        self.image_cut_model = ImageCutModel(model_configs)
        logging.info(f"ImageCutAgent initialized with model_configs: {model_configs}")


    def cut_images(self, request:ImageCutRequest) -> ImageCutResponse:
        '''
        This method is responsible for cutting images.
        '''
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
            "prompt_version": "image_cut_v3",
            "model_name": "o4-mini",
            #"model_name": "gpt-4o",
            "api_key": "66fa2e5566b4474cba373a0b69e98bd3",
            "api_version": "2025-01-01-preview",
            "azure_endpoint": "https://digitalai-eastus2-ai.openai.azure.com",
            "max_image_size": -1#2048 #-1 #2048
        }
    }
    image_cut_agent = ImageCutAgent(model_configs)
    request = ImageCutRequest(
        task_id="123",
        product_images=["./samples/T52510260108TP-高拍仪/产品/*.jpg"],
        package_images=["./samples/T52510260108TP-高拍仪/包装/*.jpg"],
        manual_images=["./samples/T52510260108TP-高拍仪/说明书/*.jpg"],
        work_dir="/code/ys_dev/tmp")

    request = ImageCutRequest(
        task_id="123",
        product_images=[""],
        package_images=["./work_dir/teqsebnceq/包装图/original/*.jpg"],
        manual_images=[],
        work_dir="./work_dir/teqsebnceq/包装图/tmp/")
    
    '''
    2025-10-30 16:19:09,992 - root - INFO - data_preprocess.py:21 - DataPreprocess initialized with model_configs: {'supported_filetype': {'jpg', 'jpeg', 'png', 'pdf'}}
2025-10-30 16:19:09,992 - root - INFO - data_preprocess.py:51 - Processing 外包装图 images: ['./work_dir/ltrod2aq3o/package_images/H54809-04257 9ft Spellcaster Witch With Spellbook_IM.pdf']
2025-10-30 16:19:11,712 - root - INFO - data_preprocess.py:51 - Processing 说明书 images: ['./work_dir/ltrod2aq3o/manual_images/H54809-04257-9ft Witch Spell Book.pdf']
    '''
    request = ImageCutRequest(
        task_id="cut_test",
        product_images=[""],
        package_images=['./work_dir/ltrod2aq3o/package_images/H54809-04257 9ft Spellcaster Witch With Spellbook_IM.pdf'],
        manual_images=['./work_dir/ltrod2aq3o/manual_images/H54809-04257-9ft Witch Spell Book.pdf'],
        work_dir="./work_dir/tmp")

    logging.info(f"request: {request}")
    response = image_cut_agent.cut_images(request)
    logging.info(f"response: {response}")
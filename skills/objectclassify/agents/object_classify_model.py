from agents.object_classify.object_classify_prompt import OBJECT_CLASSIFY_PROMPT
from agents.object_classify.object_classify_request import ObjectClassifyRequest
from agents.object_classify.object_classify_response import ObjectClassifyResponse
from openai import OpenAI
from openai import AzureOpenAI
import glob
import base64
import json
import logging
from agents.agent_utils import ModelType, ImageType
from agents.agent_utils import call_openai_llm
import traceback
from agents.multi_image_vlm_model import MultiImageVlmModel
import os
import time


'''
    基于多张图片通过VLM模型进行推理，判断玩具的类别，并给出玩具的特性。(不依赖切图)
'''
class ObjectClassifyModel:

    def __init__(self, model_configs:dict):
        self._model_configs = model_configs
        #self._model_name = model_configs['model_name']
        self._prompt = OBJECT_CLASSIFY_PROMPT[model_configs['prompt_version']]
        logging.info(f"init ObjectClassifyModel, prompt_version={model_configs['prompt_version']}")


    def get_input_images(self, request: ObjectClassifyRequest) -> list:
        image_files = []
        product_images = request.get_product_images()
        package_images = request.get_package_images()
        manual_images = request.get_manual_images()
        if product_images is not None:
            for img_path in product_images:
                if any(img_path.lower().endswith(ext) for ext in ['.jpg', '.png', '.jpeg']):
                    for image_file in glob.glob(img_path):
                        image_files.append((image_file, {"source": ImageType.PRODUCT}))
        if package_images is not None:
            for img_path in package_images:
                if any(img_path.lower().endswith(ext) for ext in ['.jpg', '.png', '.jpeg']):
                    for image_file in glob.glob(img_path):
                        image_files.append((image_file, {"source": ImageType.PACKAGE}))
        if manual_images is not None:
            for img_path in manual_images:
                if any(img_path.lower().endswith(ext) for ext in ['.jpg', '.png', '.jpeg']):
                    for image_file in glob.glob(img_path):
                        image_files.append((image_file, {"source": ImageType.MANUAL}))
        return image_files

    def classify_object(self, request: ObjectClassifyRequest) -> ObjectClassifyResponse:
        task_id = request.get_task_id()
        start_time = time.time()
        try:
            my_vlm_model = MultiImageVlmModel(model_configs=self._model_configs)
            # 获取样品图片路径下的所有图片
            image_files = self.get_input_images(request)
            logging.info(f"Found {len(image_files)} images to process, task_id={task_id}")
            if len(image_files) == 0:
                logging.error("Found 0 images, task_id={task_id}")
                return ObjectClassifyResponse(False, f"0 images!", toy_category={}, product_features={}, sub_features={})
            # 准备消息内容
            other_info = request.get_other_info() if request.get_other_info() else ""
            my_prompt = self._prompt.format(other_info=other_info)
            my_vlm_model.upload_images(image_files)
            answer_status, answer, usage = my_vlm_model.ask(my_prompt)
            cost_time = time.time() - start_time
            logging.info(f"classify_object, task_id={task_id}, cost_time={cost_time}")
            if answer_status:
                #answer is not None:
                logging.info(f"Received response from Azure OpenAI: {answer}, usage: {usage}, task_id={task_id}")
                result = json.loads(answer.replace("```json", "").replace("```", ""))
                toy_category = result.get("toy_category", {})
                product_features = result.get("product_features", {})
                sub_features = result.get("sub_features", {})
                reason = result.get("reason", "")
                return ObjectClassifyResponse(True, "success", toy_category=toy_category, product_features=product_features, sub_features=sub_features, reason=reason)
            else:
                return ObjectClassifyResponse(False, f"run failed!", toy_category={}, product_features={}, sub_features={})
        except Exception as e:
            traceback.print_exc()
            logging.error(f"failed to exec the object classify: {str(e)}, task_id={task_id}")
            return ObjectClassifyResponse(False, f"预分类失败: {str(e)}", toy_category={}, product_features={}, sub_features={})
    
if __name__ == "__main__":
    # 配置日志
    os.makedirs("./logs", exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s',
        handlers=[
            logging.FileHandler("./logs/object_classify.log"),
            logging.StreamHandler()
        ],
        force=True
    )
    model_configs = {
                "prompt_version": "classify_to_v1",
                "model_name": "gpt-4o",
                "api_key": "b521d39f2a8748b784c254faa568b1ca",
                "api_version": "2025-01-01-preview",
                "azure_endpoint": "https://digitalai-southindia-ai.openai.azure.com"
                }
    model_configs = {
            "prompt_version": "classify_to_v1",
            "model_name": "o4-mini",
            "api_key": "66fa2e5566b4474cba373a0b69e98bd3",
            "api_version": "2025-01-01-preview",
            "azure_endpoint": "https://digitalai-eastus2-ai.openai.azure.com"
            }
    model = ObjectClassifyModel(model_configs=model_configs)
    request = ObjectClassifyRequest(
        task_id="123",
        product_images=["./samples/T52510260108TP-高拍仪/产品/*.jpg"],
        package_images=["./samples/T52510260108TP-高拍仪/包装/*.jpg"],
        manual_images=["./samples/T52510260108TP-高拍仪/说明书/*.jpg"],
        other_info="" # other_info="玩具名称：高拍仪"
    )
    response = model.classify_object(request)
    print(f"response: {response}")
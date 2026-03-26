from agents.object_classify.object_classify_request import ObjectClassifyRequest
from agents.object_classify.object_classify_response import ObjectClassifyResponse
from agents.object_classify.object_classify_model import ObjectClassifyModel
import logging
import os

class ObjectClassifyAgent:
    '''
    This agent is responsible for classifying the object by images.
    '''
    def __init__(self, model_configs:dict):
        self._model = ObjectClassifyModel(model_configs)
        logging.info(f"ObjectClassifyAgent initialized with model_configs: {model_configs}")

    def classify_object(self, request:ObjectClassifyRequest) -> ObjectClassifyResponse:
        '''
        This method is responsible for classifying the object by images.
        '''
        logging.info(f"start to classify object with request: {request}")
        response = self._model.classify_object(request)
        logging.info(f"end to classify object with request: {request} finished, response: {response}")
        return response


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

    # O3-mini not supoort
    # model_configs = {
    #       "prompt_version": "classify_to_v1",
    #       "api_key": "b521d39f2a8748b784c254faa568b1ca",
    #       "api_version": "2025-01-01-preview",
    #       "azure_endpoint": "https://digitalai-southindia-ai.openai.azure.com"}
    
    # gpt-4o
    model_configs = {
                "prompt_version": "classify_to_v2",
                "model_name": "gpt-4o",
                "api_key": "b521d39f2a8748b784c254faa568b1ca",
                "api_version": "2025-01-01-preview",
                "azure_endpoint": "https://digitalai-southindia-ai.openai.azure.com"
                }
    
    #o4-mini
    # model_configs = {
    #     "prompt_version": "classify_to_v2",
    #     "model_name": "o4-mini",
    #     "api_key": "66fa2e5566b4474cba373a0b69e98bd3",
    #     "api_version": "2025-01-01-preview",
    #     "azure_endpoint": "https://digitalai-eastus2-ai.openai.azure.com",
    #     "max_image_size": 2048 #-1 #2048
    # }
    # Qwen-VL-Max
    # model_configs = {
    #     "prompt_version": "classify_to_v2",
    #     "model_name": "qwen-vl-max",
    #     "api_key": "sk-1ad6d79a8ac748a782883ce6a9cfc4fd",
    #     "api_version": "2025-01-01-preview",
    #     "azure_endpoint": "https://digitalai-eastus2-ai.openai.azure.com",
    #     "max_image_size": 2048 #-1 #2048
    # }

    agent = ObjectClassifyAgent(model_configs)
    request = ObjectClassifyRequest(task_id="123",
                                    product_images=["./samples/T52510260108TP-高拍仪/产品/*.jpg"],
                                    package_images=["./samples/T52510260108TP-高拍仪/包装/*.jpg"],
                                    manual_images=["./samples/T52510260108TP-高拍仪/说明书/*.jpg"],
                                    other_info="其他信息"
                                    )

    request = ObjectClassifyRequest(task_id="123",
                                    product_images=[],
                                    package_images=["./work_dir/02q4hmn5f3jn/包装图/original/*.jpg"],
                                    manual_images=["./work_dir/02q4hmn5f3jn/说明书/original/*.jpg"],
                                    other_info=""
                                    )

    request = ObjectClassifyRequest(task_id="123",
                                    product_images= ['./work_dir/0u9kckwjwzb/产品图/original/产品1.png', './work_dir/0u9kckwjwzb/产品图/original/产品2_page_1.jpg'],
                                    package_images=['./work_dir/0u9kckwjwzb/包装图/cutted/外包装_page_1_0.jpg', './work_dir/0u9kckwjwzb/包装图/cutted/外包装_page_1_1.jpg', './work_dir/0u9kckwjwzb/包装图/cutted/外包装_page_1_2.jpg', './work_dir/0u9kckwjwzb/包装图/cutted/外包装_page_1_3.jpg', './work_dir/0u9kckwjwzb/包装图/cutted/外包装_page_1_4.jpg', './work_dir/0u9kckwjwzb/包装图/cutted/外包装_page_1_5.jpg'],
                                    manual_images=['./work_dir/0u9kckwjwzb/说明书/original/说明书_page_1.jpg'],
                                    other_info=""
                                    )
    response = agent.classify_object(request)
    print(response.get_status())
    print(response.get_message())
    print(response.get_toy_category())
    print(response.get_product_features())
    print(response.get_sub_features())

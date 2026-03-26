from agents.object_classify.object_classify_request import ObjectClassifyRequest
from agents.object_classify.object_classify_response import ObjectClassifyResponse
from agents.object_classify.object_classify_model import ObjectClassifyModel
import logging
import os
class ObjectClassifyAgent:
    def __init__(self, model_configs:dict):
        self._model = ObjectClassifyModel(model_configs)
        logging.info(f"ObjectClassifyAgent initialized with model_configs: {model_configs}")

    def classify_object(self, request:ObjectClassifyRequest) -> ObjectClassifyResponse:
        logging.info(f"start to classify object with request: {request}")
        response = self._model.classify_object(request)
        logging.info(f"end to classify object with request: {request} finished, response: {response}")
        return response

if __name__ == "__main__":
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
    
    # gpt-4o
    model_configs = {
                "prompt_version": "classify_to_v2",
                "model_name": "",
                
                }

    agent = ObjectClassifyAgent(model_configs)
    request = ObjectClassifyRequest(task_id="",
                                    product_images=[""],
                                    package_images=[""],
                                    manual_images=[""],
                                    other_info=""
                                    )

    request = ObjectClassifyRequest(
                                    )

    request = ObjectClassifyRequest(
                                    )
    response = agent.classify_object(request)
    print(response.get_status())
    print(response.get_message())
    print(response.get_toy_category())
    print(response.get_product_features())
    print(response.get_sub_features())

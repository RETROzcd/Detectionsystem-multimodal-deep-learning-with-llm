from agents.rule_check.rule_check_request import RuleCheckRequest
from agents.rule_check.rule_check_response import RuleCheckResponse
from agents.rule_check.rule_check_model import RuleCheckModel
from agents.rule_check.rule import Rule
import logging
import os
import json

'''
This agent is responsible for checking the rules.
RuleCheckAgent类
'''
class RuleCheckAgent:
    def __init__(self, model_configs:dict):
        self._model_configs = model_configs
        self._model = RuleCheckModel(model_configs)
        logging.info(f"RuleCheckAgent initialized with model_configs: {model_configs}")

    def check_rules(self, request:RuleCheckRequest) -> RuleCheckResponse:
        '''
        This method is responsible for checking the rules.
        '''     
        logging.info(f"start to check rules with request: {request}")
        response = self._model.check_rules(request)
        task_id = request.get_task_id()
        logging.info(f"end to check rules! task_id={task_id}")
        return response

if __name__ == "__main__":
    # 配置日志
    os.makedirs("./logs", exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s',
        handlers=[
            logging.FileHandler("./logs/rule_check.log"),
            logging.StreamHandler()
        ],
        force=True
    )
    model_configs = {
                # 检查必要性
                "check_necessity_prompt_version": "check_necessity_v1", 
                # 检查是否通过性
                "check_passthrough_prompt_version": "check_passthrough_v2",
                # 检查模式
                "check_mode": "multi_image_vlm",
                # 从一张图片中抽取跟rule相关的信息
                "image_keyword_extract_prompt_version": "image_keyword_extract_v2",
                # 从多张图片的关键信息中抽取跟rule相关的信息
                "merged_rule_check_prompt_version": "merged_rule_check_v2", 
                "model_name": "gpt-4o",
                "api_key": "b521d39f2a8748b784c254faa568b1ca",
                "api_version": "2025-01-01-preview",
                "azure_endpoint": "https://digitalai-southindia-ai.openai.azure.com"
                }

    model_configs = {
                # 检查必要性
                "check_necessity_prompt_version": "check_necessity_v1", 
                # 检查是否通过性
                "check_passthrough_prompt_version": "check_passthrough_v2",
                # 检查模式
                "check_mode": "multi_image_vlm",
                # 从一张图片中抽取跟rule相关的信息
                "image_keyword_extract_prompt_version": "image_keyword_extract_v2",
                # 从多张图片的关键信息中抽取跟rule相关的信息
                "merged_rule_check_prompt_version": "merged_rule_check_v2", 
                "model_name": "gpt-4o",
                "api_key": "b521d39f2a8748b784c254faa568b1ca",
                "api_version": "2025-01-01-preview",
                "azure_endpoint": "https://digitalai-southindia-ai.openai.azure.com"
                }

    # qwen-vl-max
    model_configs = {
                # 检查必要性
                "check_necessity_prompt_version": "check_necessity_v1", 
                # 检查是否通过性
                "check_passthrough_prompt_version": "check_passthrough_v2",
                # 检查模式
                "check_mode": "multi_image_vlm",
                # 从一张图片中抽取跟rule相关的信息
                "image_keyword_extract_prompt_version": "image_keyword_extract_v2",
                # 从多张图片的关键信息中抽取跟rule相关的信息
                "merged_rule_check_prompt_version": "merged_rule_check_v2", 
                "model_name": "qwen-vl-max",
                "api_key": "sk-1ad6d79a8ac748a782883ce6a9cfc4fd",
                #"api_key": "b521d39f2a8748b784c254faa568b1ca",
                "api_version": "2025-01-01-preview",
                "azure_endpoint": "https://digitalai-southindia-ai.openai.azure.com"
                }
    # o4-mini
    model_configs = {
                # 检查必要性
                "check_necessity_prompt_version": "check_necessity_v2", 
                # 检查是否通过性
                "check_passthrough_prompt_version": "check_passthrough_v3",
                # 检查模式
                "check_mode": "multi_image_vlm",
                # 从一张图片中抽取跟rule相关的信息
                "image_keyword_extract_prompt_version": "image_keyword_extract_v2",
                # 从多张图片的关键信息中抽取跟rule相关的信息
                "merged_rule_check_prompt_version": "merged_rule_check_v2", 
                "model_name": "o4-mini",
                "api_key": "66fa2e5566b4474cba373a0b69e98bd3",
                "api_version": "2025-01-01-preview",
                "azure_endpoint": "https://digitalai-eastus2-ai.openai.azure.com"
                }
    
    agent = RuleCheckAgent(model_configs)
    if False:
        request = RuleCheckRequest(task_id="999",
                               enable_cutted_images=True,
                               product_images=['./work_dir/twkl226fslj/产品图/original/产品1.png', './work_dir/twkl226fslj/产品图/original/产品2_page_1.jpg'],
                               package_images=['./work_dir/twkl226fslj/包装图/original/外包装_page_1.jpg'],
                               manual_images=["./work_dir/twkl226fslj/说明书/original/说明书_page_1.jpg"],
                               cutted_product_images= {'./work_dir/it2zwguae0k/产品图/original/产品1.png': ['./work_dir/it2zwguae0k/产品图/original/产品1.png'], './work_dir/it2zwguae0k/产品图/original/产品2_page_1.jpg': ['./work_dir/it2zwguae0k/产品图/original/产品2_page_1.jpg']},
                               cutted_package_images=  {'./work_dir/jhdow29ee4/包装图/original/外包装_page_1.jpg': ['./work_dir/jhdow29ee4/包装图/cutted/外包装_page_1_0.jpg', './work_dir/jhdow29ee4/包装图/cutted/外包装_page_1_1.jpg', './work_dir/jhdow29ee4/包装图/cutted/外包装_page_1_2.jpg', './work_dir/jhdow29ee4/包装图/cutted/外包装_page_1_3.jpg', './work_dir/jhdow29ee4/包装图/cutted/外包装_page_1_4.jpg', './work_dir/jhdow29ee4/包装图/cutted/外包装_page_1_5.jpg']},
                               cutted_manual_images={'./work_dir/it2zwguae0k/说明书/original/说明书_page_1.jpg': ['./work_dir/it2zwguae0k/说明书/original/说明书_page_1.jpg']},
                               toy_category={"Art Materials"},
                               product_features={"电池驱动的玩具", "产品特性2"},
                               sub_features={"细分特性1", "适用UPLR", "USB供电"},
                               design_age_range = "从0岁到12岁",
                               other_info="",
                               )
        rule = Rule(group_id="1", 
            rule_id="ruleid-1",
            chapter="01 General Labeling requirements", 
            title="One Time Use Products Fair Packaging and Labeling Act or All Other Products. Uniform Packaging and Labeling Regulations", 
            method="F.P. & L. Act(16 CFR 500) OR NIST Uniform Laws and Regulations Handbook 130", 
            requirements="""(1) Manufacturer, Packer, or Distributor’s Name & Address (City, State & Zip).
(2) Product Identification
(3) Net quantity of contents shall be expressed in terms of weight or mass, measure, numerical count, or combination so as to give accurate information to facilitate consumer comparison (U.S. and metric units).
            """, 
            preconditions="", #"适用UPLR", 


            audit_content="包装的主展示面上有产品名称，且名称的方向基本与主展示面的方向一致",
            exemption_clauses="""
            豁免条件，如果产品以个数卖，且通过目视可以观察到具体数量、或有真实的产品照片展示，则产品名称可以豁免。
            """,
            llm_prompt="""
            if 符合要求，输出pass， 并remark出发现的内容和判断通过的原因；if 不符合要求，输出fail， 并remark出fail的原因
            """)
        request.add_rule(rule)
        agent._model.dump_request_rules(request)
    if False:
        json_file = "./work_dir/rule_check_request_qlfq00ewsv.json"
        new_task_id = "test"
        with open(json_file, "r", encoding="utf-8") as f:
            json_data = json.load(f)
            request = RuleCheckRequest.from_json(json_data, filter_keyword="包装上需要有原产国的标识清晰可识别。")
            request.set_task_id(new_task_id)
    if False:
        json_file = "./work_dir/rule_check_request_a16ok16h4kj.json"
        new_task_id = "test"
        with open(json_file, "r", encoding="utf-8") as f:
            json_data = json.load(f)
            request = RuleCheckRequest.from_json(json_data, filter_keyword="国旗图片")
            request.set_task_id(new_task_id)

    if False:
        json_file = "./work_dir/rule_check_request_cvddie5zcfm.json"
        new_task_id = "test"
        with open(json_file, "r", encoding="utf-8") as f:
            json_data = json.load(f)
            request = RuleCheckRequest.from_json(json_data, filter_keyword="包装上需要有原产国的标识清晰可识别")
            request.set_task_id(new_task_id)

    if True:
        json_file = "./work_dir/rule_check_request_wyruy4bsy7r.json"
        new_task_id = "test"
        with open(json_file, "r", encoding="utf-8") as f:
            json_data = json.load(f)
            request = RuleCheckRequest.from_json(json_data, filter_keyword="产品上是否有产品型号、生产日期、制造商或品牌")
            request.set_task_id(new_task_id)
    response = agent.check_rules(request)
    print(response.to_json())

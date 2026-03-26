from agents.rule_check.rule_check_request import RuleCheckRequest
from agents.rule_check.rule_check_response import RuleCheckResponse
from agents.rule_check.rule_check_model import RuleCheckModel
from agents.rule_check.rule import Rule
import logging
import os
import json
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
             ,
               
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
               
                }
    
    agent = RuleCheckAgent(model_configs)

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

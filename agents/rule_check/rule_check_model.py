from agents.rule_check.rule_check_prompt import RULE_CHECK_PROMPT
from agents.rule_check.rule_check_request import RuleCheckRequest
from agents.rule_check.rule_check_response import RuleCheckResponse
from agents.rule_check.rule import Rule
from agents.rule_check.rule_check_result import RuleCheckResult
from openai import OpenAI
from openai import AzureOpenAI
import glob
import base64
import json
import logging
from agents.agent_utils import ModelType, ImageType, RuleCheckMode
from agents.agent_utils import call_openai_llm
import traceback
from agents.multi_image_vlm_model import MultiImageVlmModel
import time
import os
from utils.condition_decider import ConditionDecider
from utils.age_range_overlap import has_age_range_overlap

'''
    基于多张图片通过VLM模型进行推理，判断玩具的类别，并给出玩具的特性。(不依赖切图)
'''
class RuleCheckModel:

    def __init__(self, model_configs: dict):
        self._model_configs = model_configs
        # check_necessity_prompt为空时，代表只用包含关系判定是否必要
        self.check_necessity_prompt_version = model_configs['check_necessity_prompt_version']
        self.check_necessity_prompt = RULE_CHECK_PROMPT[self.check_necessity_prompt_version] if self.check_necessity_prompt_version in RULE_CHECK_PROMPT else ""
        self._check_mode = model_configs['check_mode'] if 'check_mode' in model_configs else 'multi_image_vlm'
        self.check_paththrough_prompt = RULE_CHECK_PROMPT[model_configs['check_passthrough_prompt_version'] if 'check_passthrough_prompt_version' in model_configs else 'check_passthrough_prompt_v1']
        self.image_keyword_extract_prompt = RULE_CHECK_PROMPT[model_configs['image_keyword_extract_prompt_version'] if 'image_keyword_extract_prompt_version' in model_configs else 'image_keyword_extract_prompt_v1']
        self.merged_rule_check_prompt = RULE_CHECK_PROMPT[model_configs['merged_rule_check_prompt_version'] if 'merged_rule_check_prompt_version' in model_configs else 'merged_rule_check_prompt_v1']
        self.merged_batch_rule_check_prompt = RULE_CHECK_PROMPT[model_configs['merged_batch_rule_check_prompt_version'] if 'merged_batch_rule_check_prompt_version' in model_configs else 'merged_batch_rule_check_prompt_v1']
        
        self._model_name = model_configs['model_name']
        if self._model_name in [ModelType.GPT_4O, ModelType.O4_MINI, ModelType.O3_MINI]:
            self._client = AzureOpenAI(
                ?
                )
        elif self._model_name in [ModelType.QWEN_VL_MAX]:
            self._client = OpenAI(
                ?
            )
        else:
            raise ValueError(f"Invalid model name: {self._model_name}")
        self._max_workers = self._model_configs.get('max_workers', 6)
        self._debug_mode = model_configs['debug_mode'] if 'debug_mode' in model_configs else True
        logging.info(f"init RuleCheckModel, self.check_necessity_prompt_version={self.check_necessity_prompt_version}, check_mode={self._check_mode}, model_name={self._model_name}, debug_mode={self._debug_mode}, max_workers={self._max_workers}")


    def dump_request_rules(self, request: RuleCheckRequest):
        file_name = os.path.join("./work_dir", f"rule_check_request_{request.get_task_id()}.json")

        request_json = request.to_json()
        with open(file_name, "w", encoding="utf-8") as f:
            json.dump(request_json, f, ensure_ascii=False, indent=4)

    def dump_response_rules(self, response: RuleCheckResponse):
        file_name = os.path.join("./work_dir", f"rule_check_response_{response.get_task_id()}.json")
        response_json = response.to_json()
        with open(file_name, "w", encoding="utf-8") as f:
            json.dump(response_json, f, ensure_ascii=False, indent=4)

        # with open(file_name, "w") as f:
        #     check_results = response.get_check_results()
        #     print(check_results[0])
        #     for itm in check_results:
        #         rule = itm["rule"]
        #         check_result = itm["check_result"]
        #         idx = itm["idx"]
        #         f.write(f"rule_id={rule.get_rule_id()}, idx={idx}, chapter={rule.get_chapter()}, title={rule.get_title()}, method={rule.get_method()}, audit_content={rule.get_audit_content()}, preconditions={rule.get_preconditions()}, necessity_state={check_result.get_necessity_state()}, necessity_reason={check_result.get_necessity_reason()}\n")
    '''
    检查所有规则的主要实现方法:
    1. 遍历请求中的所有规则组
    2. 对每个规则:
       - 先检查规则的必要性(通过玩具类别、产品特性等判断)
       - 如果规则必要,则进行通过性检查(检查是否满足规则要求)
       - 如果规则不必要,则直接标记为通过
    3. 将所有检查结果添加到响应中
    '''
    def check_rules(self, request: RuleCheckRequest) -> RuleCheckResponse:
        task_id = request.get_task_id()
        start_time = time.time()
        rules = request.get_rules()
        logging.info(f"start to check_rules, task_id={task_id}, total_rules={len(rules)}")
        
        # 空列表检查
        if len(rules) == 0:
            error_msg = f"规则列表为空，无法进行检查！task_id={task_id}"
            print(f"===================ERROR: {error_msg}")
            logging.error(error_msg)
            response = RuleCheckResponse(False, error_msg, task_id)
            return response
        
        if self._debug_mode:
            self.dump_request_rules(request)
        response = RuleCheckResponse(True, "success", task_id)
        try:
            
            # 遍历所有规则并检查
            need_passthrough_rules = []
            import concurrent.futures
            import threading
            
            max_workers = self._max_workers
            
            # 收集所有需要检查的规则
            all_rules_to_check = []
            for idx, rule in enumerate(rules):
                group_id = rule.get_group_id()
                all_rules_to_check.append((group_id, idx, rule, len(rules)))
            
            # 定义检查单个规则的函数
            def check_single_rule(rule_info):
                group_id, idx, rule, total_rules = rule_info
                try:
                    necessity_state, necessity_reason = self.check_one_rule_necessity(rule, request)
                    return rule, necessity_state, necessity_reason, idx
                except Exception as e:
                    # 捕获单个规则检查时的异常，避免影响其他规则
                    rule_id = rule.get_rule_id() if rule else "unknown"
                    error_msg = f"检查必要性时出错: {str(e)}"
                    print(f"===================ERROR: rule_id={rule_id}, {error_msg}")
                    logging.error(f"check_single_rule error, rule_id={rule_id}, error={str(e)}, traceback={traceback.format_exc()}")
                    return rule, False, error_msg, idx
            
            # 使用线程池执行规则检查
            check_necessity_start_time = time.time()
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                # 提交所有任务
                future_to_rule = {executor.submit(check_single_rule, rule_info): rule_info for rule_info in all_rules_to_check}
                
                # 收集结果
                counter = 0
                for future in concurrent.futures.as_completed(future_to_rule):
                    rule, necessity_state, necessity_reason, idx = future.result()
                    rule_id = rule.get_rule_id()
                    preconditions = rule.get_preconditions()
                    audit_content = rule.get_audit_content()
                    counter += 1
                    logging.info(f"check_necessity_single_rule= {counter}/{len(future_to_rule)}, task_id={task_id}, rule_id={rule_id}, result={necessity_state}, necessity_reason={necessity_reason}, preconditions={preconditions}")
                    if necessity_state == True:
                        need_passthrough_rules.append((rule, necessity_reason, idx))
                    else:
                        # 必要性检查失败， 即是不需要的，则认为规则通过
                        checkResult = RuleCheckResult()
                        checkResult.set_necessity_state(False)
                        checkResult.set_necessity_reason(necessity_reason)
                        response.add_check_result(rule, checkResult, idx)
            
            # 调试输出：必要性检查结果统计
            total_checked = len(future_to_rule)
            necessity_false_count = len(response.get_check_results())
            necessity_true_count = len(need_passthrough_rules)
            print(f"===================DEBUG: check_necessity completed, task_id={task_id}")
            print(f"===================DEBUG: total_checked={total_checked}, necessity_false={necessity_false_count}, necessity_true={necessity_true_count}")
            logging.info(f"check_necessity completed, task_id={task_id}, total_checked={total_checked}, necessity_false={necessity_false_count}, necessity_true={necessity_true_count}")
            
            check_necessity_cost_time = time.time() - check_necessity_start_time
            logging.info(f"check_necessity_cost_time={check_necessity_cost_time}, task_id={task_id}")
            
            # 调试输出：need_passthrough_rules 数量
            print(f"===================DEBUG: need_passthrough_rules count: {len(need_passthrough_rules)}")
            print(f"===================DEBUG: current response check_results count: {len(response.get_check_results())}")

            if len(need_passthrough_rules) > 0:
                passthrough_start_time = time.time()
                logging.info(f"need_passthrough_rules: {len(need_passthrough_rules)}, task_id={task_id}")
                # 先传图
                image_files = self.generate_rule_passthrough_images(request)
                logging.info(f"Found {len(image_files)} images to process, task_id={task_id}")
                my_vlm_model = MultiImageVlmModel(model_configs=self._model_configs)
                max_image_num = 50
                # 传切图/原图
                if self._check_mode == RuleCheckMode.MULTI_IMAGE_VLM:
                    if len(image_files) <= max_image_num:
                        # 模式1: 一次上传多张图片, 多次ask: upload_images -> ask[1]->ask[1]...
                        my_vlm_model.upload_images(image_files)
                        # 再分别判定
                        # 定义检查单个规则通过性的函数
                        def check_single_rule_passthrough(rule_info):
                            rule, necessity_reason, idx = rule_info
                            passthrough_check_result = self.batch_check_rule_passthrough(rule, request, my_vlm_model, image_files)
                            passthrough_check_result.set_necessity_state(True)
                            passthrough_check_result.set_necessity_reason(necessity_reason)
                            return rule, passthrough_check_result, idx
                        
                        # 使用线程池执行规则通过性检查
                        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                            # 提交所有任务
                            future_to_rule = {executor.submit(check_single_rule_passthrough, rule_info): rule_info for rule_info in need_passthrough_rules}
                            # 收集结果
                            for counter, future in enumerate(concurrent.futures.as_completed(future_to_rule)):
                                rule, passthrough_check_result, idx = future.result()
                                logging.info(f"batch_check_rule_passthrough: {counter+1}/{len(future_to_rule)}, task_id: {task_id}, result: {passthrough_check_result}")
                                response.add_check_result(rule, passthrough_check_result, idx)
                    else:
                        # 模式1: 一次上传max_image_num张图片, 多次ask: upload_images -> ask[1]->ask[1]...
                        for i in range(0, len(image_files), max_image_num):
                            sub_images_files = image_files[i:i+max_image_num]
                            my_vlm_model.upload_images(sub_images_files)
                            # 定义检查单个规则通过性的函数
                            def check_single_rule_passthrough(rule_info):
                                rule, necessity_reason, idx = rule_info
                                passthrough_check_result = self.batch_check_rule_passthrough(rule, request, my_vlm_model, image_files)
                                passthrough_check_result.set_necessity_state(True)
                                passthrough_check_result.set_necessity_reason(necessity_reason)
                                return rule, passthrough_check_result, idx
                            
                            # 使用线程池执行规则通过性检查
                            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                                # 提交所有任务
                                future_to_rule = {executor.submit(check_single_rule_passthrough, rule_info): rule_info for rule_info in need_passthrough_rules}
                                # 收集结果
                                for counter, future in enumerate(concurrent.futures.as_completed(future_to_rule)):
                                    rule, passthrough_check_result, idx = future.result()
                                    logging.info(f"batch_check_rule_passthrough: {counter+1}/{len(future_to_rule)}, task_id: {task_id}, result: {passthrough_check_result}")
                                    response.add_sub_check_result(rule, passthrough_check_result, idx, sub_images_files)
                            my_vlm_model.clear_context()
                        # 整体再进行一次判断
                        sub_check_results = response.get_sub_check_results()
                        #self.sub_check_results[idx] = (rule, [(sub_images_files, check_result)])
                        for idx in sub_check_results:
                            rule, check_results = sub_check_results[idx]
                            merged_check_result = self.merge_batch_check_result(check_results, rule, request, my_vlm_model)
                            merged_check_result.set_necessity_state(True)
                            merged_check_result.set_necessity_reason(check_results[0][1].get_necessity_reason())
                            response.add_check_result(rule, merged_check_result, idx)

                elif self._check_mode == RuleCheckMode.SINGLE_IMAGE_VLM:
                    # 模式2: 一次上传一张，多次ask: upload_image -> ask[1]->ask[1]... -> clear -> upload_image -> ask[1]->ask[1]... 
                    rule2image_map = {} # rule_id - > [(image_path, metadata, check_result)]
                    for image_file, metadata in image_files:
                        my_vlm_model.upload_image(image_file, metadata)
                        # 再分别判定
                        for rule, _ in need_passthrough_rules:
                            if rule.get_rule_id() not in rule2image_map:
                                rule2image_map[rule.get_rule_id()] = []
                            one_image_check_result = self.extract_image_keywords(rule, image_file, metadata, request, my_vlm_model)
                            rule2image_map[rule.get_rule_id()].append((image_file, metadata, one_image_check_result))
                        my_vlm_model.clear_context()
                    # 整体再进行一次判断
                    for rule, necessity_reason, idx in need_passthrough_rules:
                        merged_check_result = self.merge_check_result(rule2image_map[rule.get_rule_id()], rule, request, my_vlm_model)
                        merged_check_result.set_necessity_state(True)
                        merged_check_result.set_necessity_reason(necessity_reason)
                        response.add_check_result(rule, merged_check_result, idx)
                passthrough_cost_time = time.time() - passthrough_start_time
                logging.info(f"passthrough_cost_time={passthrough_cost_time}, task_id={task_id}")

        except Exception as e:
            traceback.print_exc()
            error_msg = f"failed to check rules: {str(e)}"
            print(f"===================ERROR: {error_msg}")
            print(f"===================ERROR: Exception type: {type(e).__name__}")
            print(f"===================ERROR: Exception args: {e.args}")
            logging.error(error_msg)
            logging.error(f"Exception type: {type(e).__name__}, Exception args: {e.args}")
            logging.error(f"Exception traceback: {traceback.format_exc()}")
            
            # 打印异常发生时的规则数量
            try:
                rules_count = len(request.get_rules()) if request else 0
                print(f"===================ERROR: Exception occurred with {rules_count} rules in request")
                logging.error(f"Exception occurred with {rules_count} rules in request")
            except:
                pass
            
            # 即使有异常，如果已有检查结果，保留结果并添加警告信息
            existing_results_count = len(response.get_check_results())
            if existing_results_count > 0:
                warning_msg = f"部分规则检查完成（{existing_results_count}个），但检查过程中出现错误: {str(e)}"
                print(f"===================WARNING: {warning_msg}")
                logging.warning(warning_msg)
                response.set_run_status(False)
                response.set_message(warning_msg)
            else:
                # 如果没有结果，设置为完全失败
                response.set_run_status(False)
                response.set_message(str(e))
        cost_time = time.time() - start_time
        if self._debug_mode:
            self.dump_response_rules(response)
        logging.info(f"end to check_rules, task_id={task_id}, cost_time={cost_time}")
        return response
    
    # 【Toys with Functional Sharp Edges】且【年龄“48-96个月”】
    # def split_preconditions(self, preconditions: str) -> list[str]:
    #     pass
    
    '''
    通过玩具类别信息&前置条件，检查规则是否必要
    '''
    def check_one_rule_necessity(self, rule: Rule, request: RuleCheckRequest) -> bool:
        '''
        通过前置条件，检查规则是否必要
        '''
        task_id = request.get_task_id()
        toy_category = request.get_toy_category()
        product_features = request.get_product_features()
        sub_features = request.get_sub_features()
        design_age_range = request.get_design_age_range()
        
        necessity_state = False
        necessity_reason = ""
        rule_id = rule.get_rule_id()
        task_id = request.get_task_id()
        preconditions = rule.get_preconditions()
        preconditions = preconditions.strip()
        rule_age_range_label = rule.get_age_range_label()
        rule_age_range_label = rule_age_range_label.replace("【", "").replace("】", "").strip()
        if preconditions is None or preconditions == "":
            logging.info(f"rule_id={rule_id}, task_id={task_id}, preconditions is None or preconditions == '', return True")
            return True, "preconditions is None"
        elif len(self.check_necessity_prompt) == 0: 
            # 如果是空，通过包含关系判定是否符合
            toy_category2 = [ "【" + item.replace(' ', '') + "】" for item in toy_category]
            try:
                if ConditionDecider.decide(toy_category2, preconditions):
                    logging.info(f"rule_id={rule_id}, task_id={task_id}, preconditions={preconditions}, toy_category={toy_category}, return True")
                    # 继续判断年龄段
                    if design_age_range is None or design_age_range == "" or rule_age_range_label is None or rule_age_range_label == "":
                        return True, f"命中{preconditions}、{rule_age_range_label}类别"
                    else:
                        # 判断年龄段
                        if has_age_range_overlap(design_age_range, rule_age_range_label):
                            return True, f"命中{preconditions}----{rule_age_range_label}类别"
                        else:
                            return False, f"未命中{preconditions}----{rule_age_range_label}类别"
                else:
                    return False, f"未命中{preconditions}类别"
            except ValueError as e:
                # 捕获表达式格式错误
                error_msg = f"表达式格式错误: {str(e)}"
                print(f"===================ERROR: rule_id={rule_id}, preconditions={preconditions}, {error_msg}")
                logging.error(f"ConditionDecider.decide error, rule_id={rule_id}, preconditions={preconditions}, error={error_msg}")
                return False, error_msg
            except Exception as e:
                # 捕获其他异常
                error_msg = f"检查必要性时出错: {str(e)}"
                print(f"===================ERROR: rule_id={rule_id}, preconditions={preconditions}, {error_msg}")
                logging.error(f"check_one_rule_necessity error, rule_id={rule_id}, preconditions={preconditions}, error={error_msg}, traceback={traceback.format_exc()}")
                return False, error_msg
        else:
            # 检查前置条件 通过模型判断
             # 准备消息内容
            prompt = self.check_necessity_prompt.format(toy_category=toy_category, product_features=product_features, sub_features=sub_features, design_age_range=design_age_range, preconditions=preconditions)
            content = [{"type": "text", "text": prompt}]
            # 发送请求
            try:
                response = call_openai_llm(self._client, self._model_name, content)
                if response is not None:
                    result = json.loads(response.choices[0].message.content.replace("```json", "").replace("```", ""))
                    my_status = result["status"] if 'status' in  result else False
                    #logging.info(f"check_rule_necessity result: {result}, status: {my_status}, preconditions: {preconditions}, task_id: {task_id}")
                    if "status" in result and (result["status"] == True or str(result["status"]) in ["true", "True"]):
                        necessity_state = True
                        necessity_reason = result["reason"] if "reason" in result else ""
                    else:
                        necessity_state = False
                        necessity_reason = result["reason"] if "reason" in result else ""
            except Exception as e:
                logging.error(f"Error checking rule necessity: {str(e)} {rule_id}")
                necessity_state = False 
                necessity_reason = "run failed"
        return necessity_state, necessity_reason

    '''
        组装图片数据地址
        force_original_image: 是否强制把原图放进去
    '''
    def generate_rule_passthrough_images(self, request: RuleCheckRequest, force_original_image: bool = True):
        images = []
        enable_cutted_images = request.get_enable_cutted_images()
        
        if enable_cutted_images:
            # 处理切割后的图片
            image_sources = [
                (request.get_cutted_product_images(), ImageType.PRODUCT),
                (request.get_cutted_package_images(), ImageType.PACKAGE),
                (request.get_cutted_manual_images(), ImageType.MANUAL)
            ]
            added_image_files = []
            for source_dict, image_type in image_sources:
                for cutted_imgs in source_dict.values():
                    # 
                    images.extend((image_file, {"图片类型": image_type, "图片地址": image_file}) for image_file in cutted_imgs)
                    added_image_files.extend(cutted_imgs)
            if force_original_image:
                # 放进原图
                original_image_sources = [
                    (request.get_product_images(), ImageType.PRODUCT),
                    (request.get_package_images(), ImageType.PACKAGE),
                    (request.get_manual_images(), ImageType.MANUAL)
                ]
                for image_list, image_type in original_image_sources:
                    for image_file in image_list:
                        if image_file not in added_image_files:
                            # , "图片地址": image_file
                            images.append((image_file, {"图片类型": image_type, "图片地址": image_file}))

        else:
            # 处理原始图片
            image_patterns = [
                (request.get_product_images(), ImageType.PRODUCT),
                (request.get_package_images(), ImageType.PACKAGE),
                (request.get_manual_images(), ImageType.MANUAL)
            ]
            for img_pattern, image_type in image_patterns:
                for item in img_pattern:
                    imgs = glob.glob(item)
                    #logging.info(f"imgs: {imgs}, image_type: {image_type}")
                    images.extend((image_file, {"图片类型": image_type, "图片地址": image_file}) for image_file in imgs)
        return images

    '''
        从一张图片中抽取跟rule相关的信息
    '''
    def extract_image_keywords(self, rule: Rule, image_file, image_type, request: RuleCheckRequest, vlm_model: MultiImageVlmModel) -> RuleCheckResult:        
        checkResult = RuleCheckResult()
        rule_id = rule.get_rule_id()
        audit_content = rule.get_audit_content()
        exemption_clauses = rule.get_exemption_clauses()
        enable_cutted_images = request.get_enable_cutted_images()
        llm_prompt = rule.get_llm_prompt()
        prompt = self.image_keyword_extract_prompt.format(image_type=image_type, audit_content=audit_content, exemption_clauses=exemption_clauses, llm_prompt=llm_prompt) 
        status, answer, usage = vlm_model.ask(prompt)
        if status:
            result_raw = answer.replace("```json", "").replace("```", "")
            logging.info(f"extract_image_keywords result: {result_raw}, usage: {usage}, image_file: {image_file}, image_type: {image_type}, rule_id: {rule_id}")
            result = json.loads(result_raw)
            checkResult.add_pic(image_file)
            if "pass" in result and (result["pass"] == True or str(result["pass"]) in ["true", "True"]):
                # 检查通过
                checkResult.set_pass_status(True)
                checkResult.set_llm_response(result_raw)
            else:
                checkResult.set_pass_status(False)
                checkResult.set_llm_response(result_raw)
        else:
            checkResult.set_run_status(False)
        return checkResult

    '''
        从一张图片中抽取跟rule相关的信息
    '''
    def merge_check_result(self, sub_check_results: list[RuleCheckResult], rule: Rule, request: RuleCheckRequest, vlm_model: MultiImageVlmModel) -> RuleCheckResult:
        checkResult = RuleCheckResult()
        audit_content = rule.get_audit_content()
        exemption_clauses = rule.get_exemption_clauses()
        task_id =request.get_task_id()
        enable_cutted_images = request.get_enable_cutted_images()
        llm_prompt = rule.get_llm_prompt()
        image_analysis_result = []
        image_analysis_result_str = ""
        for image_file, metadata, one_image_check_result in sub_check_results:
            if one_image_check_result.get_run_status() == False:
                continue
            my_result = {}
            my_result["image_path"] = image_file
            my_result["analysis_result"] = one_image_check_result.get_llm_response()
            image_analysis_result.append(my_result)
            image_analysis_result_str += f"图片地址: {image_file}, 分析结果: {one_image_check_result.get_llm_response()}\n"
        image_analysis_result = json.dumps(image_analysis_result)
        prompt = self.merged_rule_check_prompt.format(image_analysis_result=image_analysis_result_str, audit_content=audit_content, exemption_clauses=exemption_clauses, llm_prompt=llm_prompt) 
        
        #logging.info(f"merged_rule_check_prompt: {prompt}, task_id: {task_id}")
        
        status, answer, usage = vlm_model.ask(prompt)
        if status:
            result = answer.replace("```json", "").replace("```", "")
            logging.info(f"merge_check_result result: {result}, usage: {usage}")
            result = json.loads(result)
            if "pass" in result and result["pass"] == True:
                # 检查通过
                checkResult.set_pass_status(True)
                #if "reason" in result:
                #    checkResult.set_llm_response(result["reason"])
                if "remark" in result:
                    checkResult.set_llm_response(result["remark"])
                if "reason" in result:
                    checkResult.set_reason(result["reason"])
                if "image_path" in result:
                    for image_path in result["image_path"]:
                        checkResult.add_pic(image_path)
            else:
                checkResult.set_pass_status(False)
                #if "reason" in result:
                #    checkResult.set_llm_response(result["reason"])
                if "remark" in result:
                    checkResult.set_llm_response(result["remark"])
                if "reason" in result:
                    checkResult.set_reason(result["reason"])
                
        else:
            checkResult.set_run_status(False)
        return checkResult

    '''
        从一张图片中抽取跟rule相关的信息
    '''
    def merge_batch_check_result(self, sub_check_results: list[(list[str], RuleCheckResult)], rule: Rule, request: RuleCheckRequest, vlm_model: MultiImageVlmModel) -> RuleCheckResult:
        checkResult = RuleCheckResult()
        audit_content = rule.get_audit_content()
        exemption_clauses = rule.get_exemption_clauses()
        task_id =request.get_task_id()
        enable_cutted_images = request.get_enable_cutted_images()
        llm_prompt = rule.get_llm_prompt()
        image_analysis_result = []
        image_analysis_result_str = ""
        for batch_idx, (image_full_paths, one_image_check_result) in enumerate(sub_check_results):
            if one_image_check_result.get_run_status() == False:
                continue
            my_result = {}
            pass_status = one_image_check_result.get_pass_status()
            if pass_status is None:
                pass_status = "NA"
            elif pass_status == True:
                pass_status = "pass"
            elif pass_status == False:
                pass_status = "fail"
            pics = one_image_check_result.get_pics()
            my_result["image_paths"] = pics
            content = one_image_check_result.get_llm_response()
            remark = one_image_check_result.get_remark()
            my_result["content"] = content
            reason = one_image_check_result.get_reason()
            my_result["reason"] = one_image_check_result.get_reason()
            image_analysis_result.append(my_result)
            image_analysis_result_str += f"第{batch_idx}组图片分析情况，结论(result): {pass_status}, 核心发现摘要(remark): {remark}, 相关图片地址(image_path): {pics}, 提取内容(content): {content}, 原因(reason): {reason}\n"
        prompt = self.merged_batch_rule_check_prompt.format(image_analysis_result=image_analysis_result_str, audit_content=audit_content, exemption_clauses=exemption_clauses, llm_prompt=llm_prompt) 
        
        #logging.info(f"merged_rule_check_prompt: {prompt}, task_id: {task_id}")
        
        status, answer, usage = vlm_model.ask(prompt)
        if status:
            result = answer.replace("```json", "").replace("```", "")
            logging.info(f"merge_check_result result: {result}, usage: {usage}")
            result = json.loads(result)
            if ("pass" in result and result["pass"] == True) or ("result" in result and result["result"] == "pass"):
                # 检查通过
                checkResult.set_pass_status(True)
                if "remark" in result:
                    checkResult.set_remark(result["remark"])
                if "content" in result:
                    checkResult.set_llm_response(result["content"])
                if "reason" in result:
                    checkResult.set_reason(result["reason"]) 
                if "image_path" in result:
                    for image_path in result["image_path"]:
                        checkResult.add_pic(image_path)
            elif ("pass" in result and result["pass"] == False) or ("result" in result and result["result"] == "fail"):
                checkResult.set_pass_status(False)
                if "reason" in result:
                    checkResult.set_reason(result["reason"])
                if "remark" in result:
                    checkResult.set_remark(result["remark"])
                if "content" in result:
                    checkResult.set_llm_response(result["content"])
            else: # NA: 无法判断
                checkResult.set_pass_status(None)
                if "reason" in result:
                    checkResult.set_reason(result["reason"])
                if "remark" in result:
                    checkResult.set_remark(result["remark"])
                if "content" in result:
                    checkResult.set_llm_response(result["content"])  
        else:
            checkResult.set_run_status(False)
        return checkResult

    '''
    检查一条规则: 依据audit_content、exemption_clauses
    '''
    def batch_check_rule_passthrough(self, rule: Rule, request: RuleCheckRequest, vlm_model: MultiImageVlmModel, image_files) -> RuleCheckResult:
        checkResult = RuleCheckResult()
        rule_id = rule.get_rule_id()
        audit_content = rule.get_audit_content()
        exemption_clauses = rule.get_exemption_clauses()
        llm_prompt = rule.get_llm_prompt()
        enable_cutted_images = request.get_enable_cutted_images()
        total_image_num = len(request.get_product_images()) + len(request.get_package_images()) + len(request.get_manual_images())
        image_basic_info = f"用户共上传了{total_image_num}张图片, 其中，产品图片: {len(request.get_product_images())}张, 包装图片: {len(request.get_package_images())}张, 说明书图片: {len(request.get_manual_images())}张"
        logging.info(f"image_basic_info: {image_basic_info}")
        prompt = self.check_paththrough_prompt.format(audit_content=audit_content, exemption_clauses=exemption_clauses, llm_prompt=llm_prompt, image_basic_info=image_basic_info) 
        status, answer, usage = vlm_model.ask(prompt)
        if status:
            result = answer.replace("```json", "").replace("```", "")
            logging.info(f"check_images result: {result}, usage: {usage}")
            result = json.loads(result)
            if ("pass" in result and result["pass"] == True) or ("result" in result and result["result"] == "pass"):
                # 检查通过
                checkResult.set_pass_status(True)
                if "reason" in result:
                    checkResult.set_reason(result["reason"])
                if "remark" in result:
                    checkResult.set_remark(result["remark"])
                if "content" in result:
                    checkResult.set_llm_response(result["content"])
                if "image_path" in result:
                    image_paths = result["image_path"]
                    for image_id in image_paths:
                        try:
                            if int(image_id) <= len(image_files) and int(image_id) > 0:
                                #print(image_files[int(image_id) - 1][1])
                                real_image = image_files[int(image_id) - 1][1]["图片地址"]
                                checkResult.add_pic(real_image)
                        except Exception as e:
                            logging.error(traceback.format_exc())
                            logging.error(f"Error adding image: {str(e)}, image_id={image_id}, len(image_files)={len(image_files)}, image_paths={image_paths}")
            elif ("pass" in result and result["pass"] == False) or ("result" in result and result["result"] == "fail"):
                checkResult.set_pass_status(False)
                if "reason" in result:
                    checkResult.set_reason(result["reason"])
                if "remark" in result:
                    checkResult.set_remark(result["remark"])
                if "content" in result:
                    checkResult.set_llm_response(result["content"])
            else: # NA: 无法判断
                checkResult.set_pass_status(None)
                if "reason" in result:
                    checkResult.set_reason(result["reason"])
                if "remark" in result:
                    checkResult.set_remark(result["remark"])
                if "content" in result:
                    checkResult.set_llm_response(result["content"])
        else:
            checkResult.set_run_status(False)
        return checkResult


    '''
    检查一条规则: 依据audit_content、exemption_clauses
    '''
    '''
    def check_rule_passthrough(self, rule: Rule, request: RuleCheckRequest) -> RuleCheckResult:
        checkResult = RuleCheckResult()
        rule_id = rule.get_rule_id()
        audit_content = rule.get_audit_content()
        exemption_clauses = rule.get_exemption_clauses()
        enable_cutted_images = request.get_enable_cutted_images()
        # TODO 
        if enable_cutted_images:
            # 遍历切割后的产品图片
            for product_img, cutted_imgs in request.get_cutted_product_images().items():
                result = self.check_images(ImageType.PRODUCT, cutted_imgs, audit_content, exemption_clauses)
                if result.get_pass_status():
                    checkResult.set_pass_status(True)
                    checkResult.set_llm_response(result.get_llm_response())
                    for img in cutted_imgs:
                        checkResult.add_pic(img)
                    return checkResult

            # 遍历切割后的包装图片
            for package_img, cutted_imgs in request.get_cutted_package_images().items():
                result = self.check_images(ImageType.PACKAGE, cutted_imgs, audit_content, exemption_clauses)
                if result.get_pass_status():
                    checkResult.set_pass_status(True)
                    checkResult.set_llm_response(result.get_llm_response())
                    for img in cutted_imgs:
                        checkResult.add_pic(img)
                    return checkResult

            # 遍历切割后的说明书图片
            for manual_img, cutted_imgs in request.get_cutted_manual_images().items():
                result = self.check_images(ImageType.MANUAL, cutted_imgs, audit_content, exemption_clauses)
                if result.get_pass_status():
                    checkResult.set_pass_status(True)
                    checkResult.set_llm_response(result.get_llm_response())
                    for img in cutted_imgs:
                        checkResult.add_pic(img)
                    return checkResult
        else:
            # 遍历产品图片
            product_imgs = []
            for product_img_pattern in request.get_product_images():
                product_img = glob.glob(product_img_pattern)
                product_imgs.extend(product_img)
            logging.info(f"start to check product_imgs: {product_imgs}, rule_id: {rule_id}")
            if len(product_imgs) > 0:
                result = self.check_images(ImageType.PRODUCT, product_imgs, audit_content, exemption_clauses)
                logging.info(f"end to check product_imgs: {product_imgs}, rule_id: {rule_id}, audit_content: {audit_content}, exemption_clauses: {exemption_clauses}, result: {result}")
                if result.get_pass_status():
                    checkResult.set_pass_status(True)
                    checkResult.set_llm_response(result.get_llm_response())
                    checkResult.add_pic(product_imgs)
                    return checkResult
            # 遍历包装图片
            package_imgs = []
            for package_img_pattern in request.get_package_images():
                package_img = glob.glob(package_img_pattern)
                package_imgs.extend(package_img)
            logging.info(f"start to check package_imgs: {package_imgs}, rule_id: {rule_id}")
            if len(package_imgs) > 0:
                result = self.check_images(ImageType.PACKAGE, package_imgs, audit_content, exemption_clauses)
                logging.info(f"end to check package_imgs: {package_imgs}, rule_id: {rule_id}, audit_content: {audit_content}, exemption_clauses: {exemption_clauses}, result: {result}")
                if result.get_pass_status():
                    checkResult.set_pass_status(True)
                    checkResult.set_llm_response(result.get_llm_response())
                    checkResult.add_pic(package_imgs)
                    return checkResult
            # 遍历说明书图片
            manual_imgs = []
            for manual_img_pattern in request.get_manual_images():
                manual_img = glob.glob(manual_img_pattern)
                manual_imgs.extend(manual_img)
            logging.info(f"start to check manual_imgs: {manual_imgs}, rule_id: {rule_id}")
            if len(manual_imgs) > 0:
                result = self.check_images(ImageType.MANUAL, manual_imgs, audit_content, exemption_clauses)
                logging.info(f"end to check manual_imgs: {manual_imgs}, rule_id: {rule_id}, audit_content: {audit_content}, exemption_clauses: {exemption_clauses}, result: {result}")
                if result.get_pass_status():
                    checkResult.set_pass_status(True)
                    checkResult.set_llm_response(result.get_llm_response())
                    checkResult.add_pic(manual_imgs)
                    return checkResult
        return checkResult
    '''
            
    '''
        检查多张图片, 支持单张、多张
        image_type: 图片类型, 如product、package、manual
        image_files: 图片文件列表
        audit_content: 审核内容
        exemption_clauses: 豁免条款
    '''
    '''
    def check_images(self, image_type, image_files: list[str], audit_content: str, exemption_clauses: str) -> RuleCheckResult:
        # 准备消息内容
        checkResult = RuleCheckResult()
        try:
            prompt = self.check_paththrough_prompt.format(image_type=image_type, audit_content=audit_content, exemption_clauses=exemption_clauses) 
            content = [{"type": "text", "text": prompt}]
            
            # 添加所有图片到消息内容
            for img_path in image_files:
                with open(img_path, "rb") as image_file:
                    content.append({
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{base64.b64encode(image_file.read()).decode()}"
                        }
                    })
            
            model_name = self._model_name
            response = None
            response = call_openai_llm(self.client, self._model_name, content)
            if response is not None:
                result = response.choices[0].message.content.replace("```json", "").replace("```", "")
                logging.info(f"check_images result: {result}")
                result = json.loads(result)
                if "pass" in result and result["pass"] == True:
                    # 检查通过
                    checkResult.set_pass_status(True)
                    if "reason" in result:
                        checkResult.set_llm_response(result["reason"])
                    for image_path in image_files:
                        checkResult.add_pic(image_path)
                else:
                    checkResult.set_pass_status(False)
                    if "reason" in result:
                        checkResult.set_llm_response(result["reason"])
            else:
                checkResult.set_run_status(False)
        except Exception as e:
            traceback.print_exc()
            logging.error(f"Error checking rule paththrough: {str(e)}")
            checkResult.set_run_status(False)
        return checkResult
    '''

        


        
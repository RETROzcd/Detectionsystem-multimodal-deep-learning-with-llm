import gradio as gr
import os
import logging
from typing import List, Dict, Any, Optional
from result_excel_generator import ExcelGenerator
from redis_utils import MemoryStorageUtil as RedisUtil
from redis_data import RedisRuleCheckResult
from agents.test_all import read_rules
from agents.rule_check.rule_check_agent import RuleCheckAgent
from agents.rule_check.rule_check_request import RuleCheckRequest
from agents.agent_utils import ImageType


class ReviewResultTab:
    """
    审核结果Tab组件类
    负责处理玩具审核结果的显示、编辑和Excel生成功能
    """
    
    def __init__(self, redis_util: RedisUtil, model_config: Dict[str, Any]):
        self.redis_util = redis_util
        self.model_config = model_config
        self.max_chapters = 200
        self.components = {}
        
    def create_ui(self) -> gr.Tab:
        with gr.Tab("审核结果") as review_tab:
            # 创建所有UI组件
            self._create_task_details_components()
            self._create_review_result_components()
            self._create_review_chapters_components()
            self._create_excel_components()
            # 设置事件处理器
            self._setup_event_handlers()
        return review_tab
    
    def _create_task_details_components(self):
        """创建任务详情相关组件"""
        gr.Markdown("## 任务详情")
        self.components['task_details_md'] = gr.Markdown("", visible=False)
    
    def _create_review_result_components(self):
        """创建审核结果相关组件"""
        gr.Markdown("## 审核结果")
        self.components['check_result_md'] = gr.Progress(label="审核进度", visible=True)
    
    def _create_review_chapters_components(self):
        """创建审核章节相关组件"""
        self.components['review_outputs'] = []
        self.components['acc_groups'] = []
        for i in range(self.max_chapters):
            with gr.Accordion(open=True, visible=False) as acc_group:
                self.components['acc_groups'].append(acc_group)
                
                # 章节标题
                with gr.Row():
                    chapter_title = gr.HTML(
                        f"[待定]", 
                        visible=True, 
                        elem_id=f"chapter_title_{i}", 
                        interactive=False, 
                        show_label=False, 
                        lines=1
                    )
                    self.components['review_outputs'].append(chapter_title)
                # 规则信息
                with gr.Row():
                    title_md = gr.HTML(
                        "**标题 [待定]**", 
                        visible=True, 
                        elem_id=f"title_md_{i}", 
                        interactive=False, 
                        show_label=False, 
                        lines=3
                    )
                    self.components['review_outputs'].append(title_md)
                    
                    regulation_md = gr.HTML(
                        "**[待定]**", 
                        visible=True, 
                        elem_id=f"regulation_md_{i}", 
                        interactive=False, 
                        show_label=False, 
                        lines=3
                    )
                    self.components['review_outputs'].append(regulation_md)
                    
                    requirements_md = gr.Textbox(
                        "**[待定]**", 
                        visible=True, 
                        elem_id=f"requirements_md_{i}", 
                        interactive=False, 
                        show_label=False, 
                        lines=3
                    )
                    self.components['review_outputs'].append(requirements_md)
                    
                    preconditions_md = gr.Textbox(
                        "**[待定]**", 
                        visible=False, 
                        elem_id=f"preconditions_md_{i}", 
                        interactive=False, 
                        show_label=False, 
                        lines=3
                    )
                    self.components['review_outputs'].append(preconditions_md)
                    
                    exemption_clauses_md = gr.Textbox(
                        "**[待定]**", 
                        visible=False, 
                        elem_id=f"exemption_clauses_md_{i}", 
                        interactive=False, 
                        show_label=False, 
                        lines=3
                    )
                    self.components['review_outputs'].append(exemption_clauses_md)
                
                # 审核内容区域
                with gr.Row(equal_height=False):
                    # 左侧：描述和证据图片
                    with gr.Column(scale=3, elem_classes=["bg-light-blue"]):
                        description = gr.Textbox(
                            f"[待定]", 
                            elem_id=f"description_{i}", 
                            interactive=False, 
                            show_label=False, 
                            lines=3
                        )
                        self.components['review_outputs'].append(description)
                        
                        # 证据图片（最多10张）
                        for j in range(10):
                            evidence_img = gr.Image(
                                value=None, 
                                label=f"证据", 
                                height=10, 
                                width=10, 
                                interactive=False, 
                                elem_id=f"evidence_img_{i}_{j}"
                            )
                            self.components['review_outputs'].append(evidence_img)
                    
                    # 中间：AI结论
                    with gr.Column(scale=3, elem_classes=["bg-light-green"]):
                        ai_conclusion = gr.Textbox(
                            f"[待定]", 
                            elem_id=f"ai_conclusion_{i}", 
                            interactive=False, 
                            show_label=False, 
                            lines=3
                        )
                        ai_rule = gr.Textbox(
                            "[待定]", 
                            elem_id=f"ai_rule_{i}", 
                            interactive=False, 
                            show_label=False, 
                            lines=3
                        )
                        self.components['review_outputs'].append(ai_conclusion)
                        self.components['review_outputs'].append(ai_rule)
                    
                    # 右侧：人工审核
                    with gr.Column(scale=3, elem_classes=["bg-light-yellow"]):
                        is_error = gr.Checkbox(label="错误", elem_id="is_error")
                        correct_conclusion = gr.Textbox(
                            placeholder="请输入正确结论", 
                            lines=2, 
                            show_label=False, 
                            elem_id="correct_conclusion"
                        )
                        error_reason = gr.Textbox(
                            placeholder="输入错误说明", 
                            lines=2, 
                            show_label=False, 
                            elem_id="error_reason"
                        )
                        
                        self.components['review_outputs'].append(is_error)
                        self.components['review_outputs'].append(correct_conclusion)
                        self.components['review_outputs'].append(error_reason)
    
    def _create_excel_components(self):
        """创建Excel生成相关组件"""
        self.components['generate_excel_btn'] = gr.Button(
            "勘误完成, 生成数据", 
            variant="primary", 
            size="lg", 
            visible=False
        )
        self.components['download_excel_file'] = gr.File(
            label="下载Excel文件", 
            interactive=False, 
            visible=False
        )
    
    def _setup_event_handlers(self):
        """设置事件处理器"""
        # 生成Excel事件
        self.components['generate_excel_btn'].click(
            self._generate_excel,
            inputs=self.components['review_outputs'],
            outputs=[self.components['download_excel_file']]
        )
    
    def show_task_details(self, 
                         product_files: List[Any], 
                         packaging_files: List[Any], 
                         description_files: List[Any], 
                         supplement: str, 
                         image_tiling_algorithm: str, 
                         ai_model: str, 
                         toy_category: List[str], 
                         features: List[str], 
                         sub_features: List[str], 
                         age_from: str, 
                         age_to: str, 
                         request: gr.Request) -> gr.update:
        """
        显示任务详情
        
        Args:
            product_files: 产品文件列表
            packaging_files: 包装文件列表
            description_files: 说明书文件列表
            supplement: 补充说明
            image_tiling_algorithm: 是否使用分图算法
            ai_model: AI模型
            toy_category: 玩具类别
            features: 产品特性
            sub_features: 细分特性
            age_from: 起始年龄
            age_to: 结束年龄
            request: Gradio请求对象
            
        Returns:
            gr.update: 更新后的任务详情组件
        """
        if self.redis_util.exists_key(request.session_hash):
            redis_data = self.redis_util.get_value(request.session_hash)
        else:
            return "未发现任务"
        
        # 生成任务详情的Markdown内容
        md = self._format_task_details_markdown(
            request.session_hash,
            product_files,
            packaging_files,
            description_files,
            supplement,
            image_tiling_algorithm,
            ai_model,
            toy_category,
            features,
            sub_features,
            age_from,
            age_to
        )
        
        return gr.update(value=md, visible=True)
    
    def _format_task_details_markdown(self, 
                                    session_hash: str, 
                                    product_files: List[Any], 
                                    packaging_files: List[Any], 
                                    description_files: List[Any], 
                                    supplement: str, 
                                    image_tiling_algorithm: str, 
                                    ai_model: str, 
                                    toy_category: List[str], 
                                    features: List[str], 
                                    sub_features: List[str], 
                                    age_from: str, 
                                    age_to: str) -> str:
        """
        格式化任务详情为Markdown格式
        
        Args:
            session_hash: 会话哈希
            product_files: 产品文件列表
            packaging_files: 包装文件列表
            description_files: 说明书文件列表
            supplement: 补充说明
            image_tiling_algorithm: 是否使用分图算法
            ai_model: AI模型
            toy_category: 玩具类别
            features: 产品特性
            sub_features: 细分特性
            age_from: 起始年龄
            age_to: 结束年龄
            
        Returns:
            格式化的Markdown字符串
        """
        return f"""
| 项目             | 内容 |
|------------------|------|
| **任务ID**       | {session_hash} |
| **产品文件**     | {', '.join([os.path.basename(product_file.name) for product_file in product_files]) if product_files else '未上传'} |
| **包装文件**     | {', '.join([os.path.basename(packaging_file.name) for packaging_file in packaging_files]) if packaging_files else '未上传'} |
| **说明书**       | {', '.join([os.path.basename(description_file.name) for description_file in description_files]) if description_files else '未上传'} |
| **补充说明**     | {supplement} |
| **是否使用分图算法** | {image_tiling_algorithm} |
| **AI模型**       | {ai_model} |
| **玩具类别**     | {', '.join(toy_category) if toy_category else '未选择'} |
| **产品特性**     | {', '.join(features) if features else '未选择'} |
| **细分特性**     | {', '.join(sub_features) if sub_features else '未选择'} |
| **设计年龄**     | {age_from} 到 {age_to} |
"""
    
    def _generate_excel(self, request: gr.Request, *review_outputs: Any) -> Optional[str]:
        """
        生成Excel文件
        
        Args:
            request: Gradio请求对象
            review_outputs: 审核输出数据
            
        Returns:
            str: Excel文件路径或None
        """
        excel_generator = ExcelGenerator()
        try:
            excel_path = excel_generator.generate_review_excel(review_outputs)
            
            if self.redis_util.exists_key(request.session_hash):
                redis_data = self.redis_util.get_value(request.session_hash)
                print(f"redis_data: {redis_data}")
                redis_data.rule_check_results = []
                
                # 解析审核输出数据
                self._parse_review_outputs_to_redis(review_outputs, redis_data)
                
                print(f"redis_data.rule_check_results: {redis_data.rule_check_results}")
                self.redis_util.set_value(request.session_hash, redis_data)
                print(f"request.session_hash={request.session_hash}===")
                print(f"redis_util.get_value: {self.redis_util.get_value(request.session_hash)}")
            else:
                print(f"redis_data not exists")
                return None
                
            return excel_path
        except Exception as e:
            print(f"生成Excel文件时出错: {e}")
            return None
    
    def _parse_review_outputs_to_redis(self, review_outputs: List[Any], redis_data: Any):
        """
        解析审核输出数据并保存到Redis
        
        Args:
            review_outputs: 审核输出数据列表
            redis_data: Redis数据对象
        """
        for index in range(0, len(review_outputs), 22):
            if review_outputs[index] is None or len(review_outputs[index]) == 0:
                break
            
            rule_check_result = RedisRuleCheckResult()
            rule_check_result.chapter = review_outputs[index]
            rule_check_result.title = review_outputs[index+1]
            rule_check_result.method = review_outputs[index+2]
            rule_check_result.requirements = review_outputs[index+3]
            rule_check_result.preconditions = review_outputs[index+4]
            
            # 处理图片数据
            rule_check_result.pics = []
            for j in range(index+7, index+17):
                rule_check_result.pics.append(review_outputs[j])
            
            rule_check_result.llm_response = review_outputs[index+17]
            rule_check_result.llm_prompt = review_outputs[index+18]
            rule_check_result.manual_correct_conclusion = review_outputs[index+19]
            rule_check_result.manual_error_reason = review_outputs[index+20]
            rule_check_result.manual_is_error = review_outputs[index+19]
            
            redis_data.rule_check_results.append(rule_check_result)
    
    def show_task_review(self, 
                        image_tiling_algorithm: str, 
                        ai_model: str, 
                        toy_types: List[str], 
                        features: List[str], 
                        sub_features: List[str], 
                        age_from: str, 
                        age_to: str, 
                        request: gr.Request) -> List[gr.update]:
        """
        显示任务审核结果
        
        Args:
            image_tiling_algorithm: 是否使用分图算法
            ai_model: AI模型
            toy_types: 玩具类型
            features: 产品特性
            sub_features: 细分特性
            age_from: 起始年龄
            age_to: 结束年龄
            request: Gradio请求对象
            
        Returns:
            List[gr.update]: 更新后的组件列表
        """
        print(f"toy_types: {toy_types}")
        print(f"features: {features}")
        print(f"sub_features: {sub_features}")
        print(f"age_from: {age_from}")
        print(f"age_to: {age_to}")
        
        # 检查Redis数据
        if not self._update_redis_data(request.session_hash, toy_types, features, sub_features):
            return [gr.update()] * (4400 + 200 + 3)
        
        # 执行规则检查
        rule_check_response = self._perform_rule_check(
            request.session_hash, 
            image_tiling_algorithm, 
            age_from, 
            age_to
        )
        
        if not rule_check_response:
            return [gr.update()] * (4400 + 200 + 3)
        
        # 生成UI更新
        return self._generate_ui_updates(rule_check_response)
    
    def _update_redis_data(self, 
                          session_hash: str, 
                          toy_types: List[str], 
                          features: List[str], 
                          sub_features: List[str]) -> bool:
        """
        更新Redis数据
        
        Args:
            session_hash: 会话哈希
            toy_types: 玩具类型
            features: 产品特性
            sub_features: 细分特性
            
        Returns:
            bool: 更新是否成功
        """
        if self.redis_util.exists_key(session_hash):
            redis_data = self.redis_util.get_value(session_hash)
            redis_data.manual_category_and_feature_data.toy_category = toy_types
            redis_data.manual_category_and_feature_data.features = features
            redis_data.manual_category_and_feature_data.sub_features = sub_features
            self.redis_util.set_value(session_hash, redis_data)
            return True
        else:
            print(f"redis_data not exists")
            return False
    
    def _perform_rule_check(self, 
                           session_hash: str, 
                           image_tiling_algorithm: str, 
                           age_from: str, 
                           age_to: str) -> Optional[Any]:
        """
        执行规则检查
        
        Args:
            session_hash: 会话哈希
            image_tiling_algorithm: 是否使用分图算法
            age_from: 起始年龄
            age_to: 结束年龄
            
        Returns:
            规则检查响应对象或None
        """
        redis_data = self.redis_util.get_value(session_hash)
        
        if len(redis_data.rule_file_path) == 0:
            print(f"redis_data.rule_file_path is empty")
            return None
        
        # 执行规则检查
        enable_cut_images = image_tiling_algorithm == "是"
        rule_excel_file_path = redis_data.rule_file_path
        rules, annotated_results = read_rules(rule_excel_file_path, enable_human_annotated=True, select_rule_ids=None)

        rule_check_agent = RuleCheckAgent(self.model_config["rule_check_configs"])
        rule_check_request = RuleCheckRequest(
            task_id=session_hash,
            enable_cutted_images=image_tiling_algorithm == "是",
            product_images=redis_data.preprocessed_data[ImageType.PRODUCT] if ImageType.PRODUCT in redis_data.preprocessed_data else [], 
            package_images=redis_data.preprocessed_data[ImageType.PACKAGE] if ImageType.PACKAGE in redis_data.preprocessed_data else [], 
            manual_images=redis_data.preprocessed_data[ImageType.MANUAL] if ImageType.MANUAL in redis_data.preprocessed_data else [],
            cutted_product_images=redis_data.image_cut_response.get_cutted_product_images() if enable_cut_images else {},
            cutted_package_images=redis_data.image_cut_response.get_cutted_package_images() if enable_cut_images else {},
            cutted_manual_images=redis_data.image_cut_response.get_cutted_manual_images() if enable_cut_images else {},
            toy_category=redis_data.object_classify_response.get_toy_category(),
            product_features=redis_data.object_classify_response.get_product_features(),
            sub_features=redis_data.object_classify_response.get_sub_features(),
            design_age_range=f"从{age_from}岁到{age_to}岁",
            other_info=redis_data.user_input_data["other_info"]
        )

        # 添加规则
        for rule in rules:
            rule_check_request.add_rule(rule)
        
        # 执行规则检查
        rule_check_response = rule_check_agent.check_rules(rule_check_request)
        logging.info(f"rule_check_response: {rule_check_response}")
        
        return rule_check_response
    
    def _generate_ui_updates(self, rule_check_response: Any) -> List[gr.update]:
        """
        生成UI更新列表
        
        Args:
            rule_check_response: 规则检查响应对象
            
        Returns:
            List[gr.update]: UI更新列表
        """
        updates = []
        acc_updates = []
        print(f"rule_check_response.get_check_results(): {rule_check_response.get_check_results()}")
        
        # 处理检查结果
        for i, check_result in enumerate(rule_check_response.get_check_results()):
            acc_updates.append(gr.update(visible=True))
            updates.append(gr.update(visible=True, value=f"{check_result['rule'].chapter}"))
            updates.append(gr.update(value=f"{check_result['rule'].title}"))
            updates.append(gr.update(value=f"{check_result['rule'].method}"))
            updates.append(gr.update(value=f"{check_result['rule'].requirements}"))
            updates.append(gr.update(value=f"{check_result['rule'].preconditions}"))
            updates.append(gr.update(value=f"{check_result['rule'].exemption_clauses}"))
            updates.append(gr.update(value=f"{check_result['rule'].audit_content}"))
            
            # 处理证据图片
            for j in range(len(check_result['check_result'].pics)):
                updates.append(gr.update(value=check_result['check_result'].pics[j]))
            for j in range(len(check_result['check_result'].pics), 10):
                updates.append(gr.update(value=None, visible=False))
            
            updates.append(gr.update(value=f"{check_result['check_result'].pass_status}，{check_result['check_result'].llm_response}" if check_result['check_result'].necessity_state else "NA"))
            updates.append(gr.update(value=f"{check_result['rule'].llm_prompt}"))
            updates.append(gr.update())
            updates.append(gr.update())
            updates.append(gr.update())

        # 隐藏多余章节
        for i in range(len(rule_check_response.get_check_results()), self.max_chapters):
            acc_updates.append(gr.update(visible=False))
            updates.append(gr.update(value=None, visible=False))
            updates.append(gr.update(value=None, visible=False))
            updates.append(gr.update(value=None, visible=False))
            updates.append(gr.update(visible=False))
            updates.append(gr.update(value=None, visible=False))
            updates.append(gr.update(value=None, visible=False))
            updates.append(gr.update(value=None, visible=False))
            for j in range(10):
                updates.append(gr.update(value=None, visible=False))
            updates.append(gr.update(value=None, visible=False))
            updates.append(gr.update(value=None, visible=False))
            updates.append(gr.update(visible=False))
            updates.append(gr.update(visible=False))
            updates.append(gr.update(visible=False))
        
        print(f"updates: {len(updates)}")
        return [*updates, *acc_updates, gr.update(visible=False), gr.update(visible=True), gr.update(visible=True)]
    
    def get_outputs(self) -> List[Any]:
        """
        获取输出组件列表
        
        Returns:
            List[Any]: 输出组件列表
        """
        return self.components['review_outputs'] + self.components['acc_groups']
    
    def get_components_for_layout(self) -> List[Any]:
        """
        获取用于布局的组件列表
        
        Returns:
            List[Any]: 组件列表
        """
        return [
            self.components['task_details_md'],
            self.components['check_result_md'],
            *self.components['review_outputs'],
            *self.components['acc_groups'],
            self.components['generate_excel_btn'],
            self.components['download_excel_file']
        ]
    
    def get_task_details_component(self) -> gr.Markdown:
        """
        获取任务详情组件
        
        Returns:
            gr.Markdown: 任务详情组件
        """
        return self.components['task_details_md']
    
    def get_review_outputs(self) -> List[Any]:
        """
        获取审核输出组件列表
        
        Returns:
            List[Any]: 审核输出组件列表
        """
        return self.components['review_outputs']
    
    def get_accordion_groups(self) -> List[Any]:
        """
        获取手风琴组件列表
        
        Returns:
            List[Any]: 手风琴组件列表
        """
        return self.components['acc_groups']
    
    def get_excel_components(self) -> Dict[str, Any]:
        """
        获取Excel相关组件
        
        Returns:
            Dict[str, Any]: Excel组件字典
        """
        return {
            'generate_btn': self.components['generate_excel_btn'],
            'download_file': self.components['download_excel_file']
        } 
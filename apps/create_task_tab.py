import gradio as gr
import os
from typing import List, Dict, Any
from redis_utils import MemoryStorageUtil as RedisUtil
from result_excel_generator import ExcelGenerator
from redis_data import RedisRuleCheckResult

class CreateTaskTab:
    """
    创建任务Tab组件类
    负责处理玩具审核任务的表单生成、识别、分类选择等功能
    """
    def __init__(self, redis_util: RedisUtil):
        self.redis_util = redis_util
        # 变量定义（可根据需要调整）
        self.toy_types = [
            "Aquatic Toys", "Magnetic/electrical experimental sets", "含有化学品并且会产生化学反应的实验套装","纺织品服装不包含配件（care label）",
            "电动或需接不包含配件（care label）", "Crib and Playpen Toys", "Mobiles", "Stroller and Carriage Toys",
            "Simulated Protective Devices", "Electric Toys", "Toy Chests", "Ride-on Toys", "Toy Tent",
            "化妆品玩具", "Art Materials", "Stuffing toys / Stuffed toys", "Clothing，Handkerchiefs，Scarfs，socks  and hoisery",
            "Toys in Contact with Food", "Costume，Toy Disguise Costumes",""
        ]
        self.features = [
            "small part（测试年龄3-6岁）", "small ball", "marbles", "Latex balloons", "适用FLPA","适用UPLR", "含有配置品（液体，粉末，油灰，糊剂，凝胶）","Toys Intended to be assembled by an adult", "组装前有小部件，且年龄：3岁以下",
            "有尖点利边，且年龄：0-8岁", "有加压容器", "含有复合木", "复合木面积大于等于144平方英寸", "Toys with Functional Sharp Edges or Points","电池驱动的玩具", "外接电源或者接市电", "变压器充电/供电", "USB供电", "无线产品（例如27 MHz，49 MHz),WIFI或者蓝牙产品","非有意发射的B/O玩具大于1.705Hz", "通过插头接市电且频率大于等于9KHz的产品","有意发射玩具的接收器（比如遥控车）", "本身含有打开电池盖的特定工具", "产品中有白炽灯", "设计不是在水中使用的, 但是使用过程中有可能接触到水","SAR labelling"
        ]
        self.sub_features_chemical_experiment_kit_with_reactive_substances = [
            "Toxic", "Corrosive", "Irritant", "strong sensitizer","flammable", "Combustible", "Generate pressure through decomposition", "heat or other means"
        ]
        self.sub_features_battery_powered_toy = [
            "可更换电池", "不可更换电池", "纽扣电池或硬币电池", "充电电池", "铅酸充电电池", "镍铬充电电池"
        ]
        self.all_sub_features = self.sub_features_chemical_experiment_kit_with_reactive_substances + self.sub_features_battery_powered_toy
        self.components = {}

    def create_ui(self) -> gr.Tab:
        """
        创建任务Tab的UI组件
        Returns:
            gr.Tab: 创建任务Tab组件
        """
        with gr.Tab("创建任务") as create_task_tab:
            self._create_form_components()
            self._setup_event_handlers()
        return create_task_tab

    def _create_form_components(self):
        """创建表单相关组件"""
        self.components['product_file'] = gr.File(label="产品", file_count="multiple")
        self.components['packaging_file'] = gr.File(label="包装", file_count="multiple")
        self.components['description_file'] = gr.File(label="说明书", file_count="multiple")
        self.components['supplement'] = gr.Textbox(label="补充说明")
        self.components['image_tiling_algorithm'] = gr.Radio(["否", "是"], label="使用切图算法")
        self.components['ai_model'] = gr.Dropdown(["o4-mini", "gpt-4o"], label="选择使用模型")
        self.components['output'] = gr.Textbox(placeholder="识别结果", lines=2, max_lines=4, show_label=False)
        self.components['start_btn'] = gr.Button("开始识别")
        self.components['toy_types_input'] = gr.CheckboxGroup(self.toy_types, label="玩具类别", visible=False, interactive=True)
        self.components['features_input'] = gr.CheckboxGroup(self.features, label="产品特性", visible=False, interactive=True)
        self.components['sub_features_input'] = gr.CheckboxGroup(self.all_sub_features, label="细分特性", visible=False, interactive=True)
        self.components['age_from_label'] = gr.Markdown("#### 设计年龄从", visible=False)
        self.components['age_from_input'] = gr.Textbox(label="输入框", placeholder="请输入设计年龄从", visible=False)
        self.components['age_from_unit'] = gr.Dropdown(["年", "月"], label="单位", value="年", visible=False)
        self.components['age_to_label'] = gr.Markdown("#### 设计年龄到", visible=False)
        self.components['age_to_input'] = gr.Textbox(label="输入框", placeholder="请输入设计年龄到", visible=False)
        self.components['age_to_unit'] = gr.Dropdown(["年", "月"], label="单位", value="年", visible=False)
        self.components['submit_btn'] = gr.Button("保存并创建审核表单", visible=False)
        self.components['submit_result'] = gr.Markdown("", visible=False)

    def _setup_event_handlers(self):
        """设置事件处理器"""
        self.components['start_btn'].click(
            self.start_recognition,
            inputs=[
                self.components['product_file'],
                self.components['packaging_file'],
                self.components['description_file'],
                self.components['supplement'],
                self.components['image_tiling_algorithm'],
                self.components['ai_model']
            ],
            outputs=[
                self.components['output'],
                self.components['toy_types_input'],
                self.components['features_input'],
                self.components['sub_features_input'],
                self.components['age_from_label'],
                self.components['age_from_input'],
                self.components['age_from_unit'],
                self.components['age_to_label'],
                self.components['age_to_input'],
                self.components['age_to_unit'],
                self.components['submit_btn']
            ]
        )
        self.components['toy_types_input'].change(
            self.toggle_sub_features,
            inputs=self.components['toy_types_input'],
            outputs=self.components['sub_features_input']
        )

    def start_recognition(self, product_files, packaging_files, description_files, supplement, image_tiling_algorithm, ai_model, request: gr.Request):
        """
        识别按钮事件处理函数（可根据实际需求实现AI识别逻辑）
        """
        # 这里只做简单模拟
        if not product_files and not packaging_files and not description_files:
            return ("请至少上传一个文件", gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update())
        result_text = f"识别完成！\n产品文件: {len(product_files) if product_files else 0} 个\n包装文件: {len(packaging_files) if packaging_files else 0} 个\n说明书: {len(description_files) if description_files else 0} 个"
        return (
            result_text,
            gr.update(visible=True, value=[self.toy_types[0]]),
            gr.update(visible=True, value=[self.features[0]]),
            gr.update(visible=True, value=[]),
            gr.update(visible=True),
            gr.update(visible=True, value="3"),
            gr.update(visible=True),
            gr.update(visible=True),
            gr.update(visible=True, value="6"),
            gr.update(visible=True),
            gr.update(visible=True)
        )

    def toggle_sub_features(self, selected_toy_types: List[str]) -> gr.update:
        """
        根据选择的玩具类型切换细分特性的显示状态
        """
        if "含有化学品并且自身产生化学反应的实验装置" in (selected_toy_types or []):
            return gr.update(visible=True)
        else:
            return gr.update(visible=False)

    def get_components_for_layout(self) -> List[Any]:
        """
        获取用于布局的组件列表
        """
        return list(self.components.values()) 
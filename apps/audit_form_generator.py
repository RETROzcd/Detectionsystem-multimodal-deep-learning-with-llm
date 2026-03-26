import gradio as gr
import logging
import os
import sys
from typing import List, Dict, Any, Optional

# 添加项目根目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.insert(0, project_root)

from redis_utils import MemoryStorageUtil as RedisUtil
from redis_data import RedisData, RedisCategoryAndFeatureData

class AuditFormGenerator:
    """
    审核表单生成器类
    负责处理玩具审核表单的生成，包括文件上传、AI识别、分类选择等功能
    """
    
    def __init__(self, redis_util: RedisUtil):
        """
        初始化审核表单生成器
        
        Args:
            redis_util: Redis工具类实例
        """
        self.redis_util = redis_util
        
        # 定义玩具类型
        self.toy_types = [
            "Aquatic Toys", 
            "Magnetic/electrical experimental sets", 
            "含有化学品并且会产生化学反应的实验套装",
            "纺织品服装不包含配件（care label）",
            "电动或需接不包含配件（care label）", 
            "Crib and Playpen Toys", 
            "Mobiles", 
            "Stroller and Carriage Toys",
            "Simulated Protective Devices", 
            "Electric Toys", 
            "Toy Chests", 
            "Ride-on Toys", 
            "Toy Tent",
            "化妆品玩具", 
            "Art Materials", 
            "Stuffing toys / Stuffed toys", 
            "Clothing，Handkerchiefs，Scarfs，socks and hoisery",
            "Toys in Contact with Food", 
            "Costume，Toy Disguise Costumes"
        ]
        
        # 定义产品特性
        self.features = [
            "small part（测试年龄3-6岁）", 
            "small ball", 
            "marbles", 
            "Latex balloons", 
            "适用FLPA",
            "适用UPLR", 
            "含有配置品（液体，粉末，油灰，糊剂，凝胶）",
            "Toys Intended to be assembled by an adult", 
            "组装前有小部件，且年龄：3岁以下",
            "有尖点利边，且年龄：0-8岁", 
            "有加压容器", 
            "含有复合木", 
            "复合木面积大于等于144平方英寸", 
            "Toys with Functional Sharp Edges or Points",
            "电池驱动的玩具", 
            "外接电源或者接市电", 
            "变压器充电/供电", 
            "USB供电", 
            "无线产品（例如27 MHz，49 MHz),WIFI或者蓝牙产品",
            "非有意发射的B/O玩具大于1.705Hz", 
            "通过插头接市电且频率大于等于9KHz的产品",
            "有意发射玩具的接收器（比如遥控车）", 
            "本身含有打开电池盖的特定工具", 
            "产品中有白炽灯", 
            "设计不是在水中使用的, 但是使用过程中有可能接触到水",
            "SAR labelling"
        ]
        
        # 定义细分特性 - 化学品实验套装
        self.sub_features_chemical_experiment_kit_with_reactive_substances = [
            "Toxic", 
            "Corrosive", 
            "Irritant", 
            "strong sensitizer",
            "flammable", 
            "Combustible", 
            "Generate pressure through decomposition", 
            "heat or other means"
        ]
        
        # 定义细分特性 - 电池驱动玩具
        self.sub_features_battery_powered_toy = [
            "可更换电池", 
            "不可更换电池", 
            "纽扣电池或硬币电池", 
            "充电电池", 
            "铅酸充电电池", 
            "镍铬充电电池"
        ]
        
        # 合并所有细分特性
        self.all_sub_features = (
            self.sub_features_chemical_experiment_kit_with_reactive_substances + 
            self.sub_features_battery_powered_toy
        )
    
    def create_form_components(self) -> Dict[str, Any]:
        """
        创建表单组件
        
        Returns:
            包含所有UI组件的字典
        """
        components = {}
        
        # 文件上传组件
        components['product_file'] = gr.File(label="产品", file_count="multiple")
        components['packaging_file'] = gr.File(label="包装", file_count="multiple")
        components['description_file'] = gr.File(label="说明书", file_count="multiple")
        
        # 基本输入组件
        components['supplement'] = gr.Textbox(label="补充说明")
        components['image_tiling_algorithm'] = gr.Radio(["否", "是"], label="使用切图算法")
        components['ai_model'] = gr.Dropdown(["o4-mini", "gpt-4o"], label="选择使用模型")
        
        # 输出组件
        components['output'] = gr.Textbox(placeholder="识别结果", lines=2, max_lines=4, show_label=False)
        components['start_btn'] = gr.Button("开始识别")
        
        # 分类选择组件（初始隐藏）
        components['toy_types_input'] = gr.CheckboxGroup(
            self.toy_types, 
            label="玩具类别", 
            visible=False, 
            interactive=True
        )
        components['features_input'] = gr.CheckboxGroup(
            self.features, 
            label="产品特性", 
            visible=False, 
            interactive=True
        )
        components['sub_features_input'] = gr.CheckboxGroup(
            self.all_sub_features, 
            label="细分特性", 
            visible=False, 
            interactive=True
        )
        
        # 年龄范围组件（初始隐藏）
        components['age_from_label'] = gr.Markdown("#### 设计年龄从", visible=False)
        components['age_from_input'] = gr.Textbox(
            label="输入框", 
            placeholder="请输入设计年龄从", 
            visible=False
        )
        components['age_from_unit'] = gr.Dropdown(["年", "月"], label="单位", value="年", visible=False)
        components['age_to_label'] = gr.Markdown("#### 设计年龄到", visible=False)
        components['age_to_input'] = gr.Textbox(
            label="输入框", 
            placeholder="请输入设计年龄到", 
            visible=False
        )
        components['age_to_unit'] = gr.Dropdown(["年", "月"], label="单位", value="年", visible=False)
        
        # 提交按钮
        components['submit_btn'] = gr.Button("保存并创建审核表单", visible=False)
        components['submit_result'] = gr.Markdown("", visible=False)
        
        return components
    
    def toggle_sub_features(self, selected_toy_types: List[str]) -> gr.update:
        """
        根据选择的玩具类型切换细分特性的显示状态
        
        Args:
            selected_toy_types: 选择的玩具类型列表
            
        Returns:
            Gradio更新对象
        """
        if "含有化学品并且会产生化学反应的实验套装" in (selected_toy_types or []):
            return gr.update(visible=True)
        else:
            return gr.update(visible=False)
    
    def process_form_data(self, 
                         product_file: Any, 
                         packaging_file: Any, 
                         description_file: Any, 
                         supplement: str, 
                         image_tiling_algorithm: str, 
                         ai_model: str, 
                         toy_types: List[str], 
                         features: List[str], 
                         sub_features: List[str], 
                         age_from: str, 
                         age_to: str) -> str:
        """
        处理表单数据并返回格式化字符串
        
        Args:
            product_file: 产品文件
            packaging_file: 包装文件
            description_file: 说明书文件
            supplement: 补充说明
            image_tiling_algorithm: 切图算法选择
            ai_model: AI模型选择
            toy_types: 玩具类型列表
            features: 产品特性列表
            sub_features: 细分特性列表
            age_from: 起始年龄
            age_to: 结束年龄
            
        Returns:
            格式化的表单数据字符串
        """
        return f"""
产品文件: {product_file.name if product_file else '未上传'}
包装文件: {packaging_file.name if packaging_file else '未上传'}
说明书: {description_file.name if description_file else '未上传'}
补充说明: {supplement}
识别模型提示词: {image_tiling_algorithm}
AI模型: {ai_model}
玩具类别: {', '.join(toy_types) if toy_types else '未选择'}
产品特性: {', '.join(features) if features else '未选择'}
细分特性: {', '.join(sub_features) if sub_features else '未选择'}
设计年龄: {age_from} 到 {age_to} 岁
"""
    
    def setup_event_handlers(self, components: Dict[str, Any], start_recognition_func: callable):
        """
        设置事件处理器
        
        Args:
            components: UI组件字典
            start_recognition_func: 开始识别函数
        """
        # 开始识别按钮事件
        components['start_btn'].click(
            start_recognition_func,
            inputs=[
                components['product_file'], 
                components['packaging_file'], 
                components['description_file'], 
                components['supplement'],
                components['image_tiling_algorithm'], 
                components['ai_model']
            ],
            outputs=[
                components['output'],
                components['toy_types_input'],
                components['features_input'],
                components['sub_features_input'],
                components['age_from_label'],
                components['age_from_input'],
                components['age_from_unit'],
                components['age_to_label'],
                components['age_to_input'],
                components['age_to_unit'],
                components['submit_btn']
            ]
        )
        
        # 玩具类型选择变化事件
        components['toy_types_input'].change(
            self.toggle_sub_features,
            inputs=components['toy_types_input'],
            outputs=components['sub_features_input']
        )
    
    def get_components_for_layout(self) -> List[Any]:
        """
        获取用于布局的组件列表
        
        Returns:
            组件列表
        """
        components = self.create_form_components()
        return [
            components['product_file'],
            components['packaging_file'],
            components['description_file'],
            components['supplement'],
            components['image_tiling_algorithm'],
            components['ai_model'],
            components['output'],
            components['start_btn'],
            components['toy_types_input'],
            components['features_input'],
            components['sub_features_input'],
            components['age_from_label'],
            components['age_from_input'],
            components['age_from_unit'],
            components['age_to_label'],
            components['age_to_input'],
            components['age_to_unit'],
            components['submit_btn'],
            components['submit_result']
        ]
    
    def get_toy_types(self) -> List[str]:
        """获取玩具类型列表"""
        return self.toy_types
    
    def get_features(self) -> List[str]:
        """获取产品特性列表"""
        return self.features
    
    def get_sub_features(self) -> List[str]:
        """获取细分特性列表"""
        return self.all_sub_features
    
    def get_chemical_sub_features(self) -> List[str]:
        """获取化学品实验套装细分特性"""
        return self.sub_features_chemical_experiment_kit_with_reactive_substances
    
    def get_battery_sub_features(self) -> List[str]:
        """获取电池驱动玩具细分特性"""
        return self.sub_features_battery_powered_toy 
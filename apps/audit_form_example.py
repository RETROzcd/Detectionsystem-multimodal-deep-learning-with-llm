import gradio as gr
import os
import sys

# 添加项目根目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.insert(0, project_root)

from audit_form_generator import AuditFormGenerator
from redis_utils import MemoryStorageUtil as RedisUtil, MemoryStorageUtil
from task_processor import TaskProcessor
from review_result_tab import ReviewResultTab

# 引入model_config（可根据实际情况调整）
model_config =  {
    "preprocess_configs": {"supported_filetype": {"pdf", "jpg", "png", "jpeg"}},
    "image_cut_configs": {   
        "sam_model_name": "FastSAM",
        "sam_model_ckpt": "./models/FastSAM-s.pt",
        "sam_device_id": "cpu",
        "sam_max_size": 512,
        "sam_conf": 0.15,
        "sam_iou": 0.5,
        "sam_occupy_ratio": 0.35, # 过滤超过这个占比的框
        "ocr_sam_iou_threshold": 0.1, # iou threshold
        "model_input_image_size": (768, 768), # 下游模型的图片输入大小(height, width)
        "cut_mode": "STACK_BOUNDING_BOX"
    },
    "rule_check_configs":  {
     ?
        }
}

# 初始化Redis工具
redis_util = MemoryStorageUtil()

# 创建审核表单生成器实例
audit_form_generator = AuditFormGenerator(redis_util)

# 创建任务处理器实例
task_processor = TaskProcessor(audit_form_generator)

# 创建审核结果Tab实例
review_result_tab = ReviewResultTab(redis_util, model_config)

# 创建Gradio界面
with gr.Blocks() as demo:
    gr.Markdown("# 审核表单生成器示例")
    
    with gr.Tabs() as tabs:
        with gr.Tab("创建任务"):
            gr.Markdown("## 审核表单生成")
            
            # 使用AuditFormGenerator创建组件
            components = audit_form_generator.create_form_components()
            
            # 布局组件
            with gr.Row():
                components['product_file']
            with gr.Row():
                components['packaging_file']
            with gr.Row():
                components['description_file']
            with gr.Row():
                components['supplement']
            with gr.Row():
                components['image_tiling_algorithm']
                components['ai_model']
            with gr.Row():
                components['output']
            with gr.Row():
                components['start_btn']
            
            # 分类选择组件
            components['toy_types_input']
            components['features_input']
            components['sub_features_input']
            
            # 年龄范围组件
            with gr.Row():
                components['age_from_label']
                components['age_from_input']
                components['age_from_unit']
                components['age_to_label']
                components['age_to_input']
                components['age_to_unit']
            
            components['submit_btn']
            components['submit_result']
            # 设置事件处理器
            audit_form_generator.setup_event_handlers(components, task_processor.start_recognition)
            # 提交按钮事件
            components['submit_btn'].click(
                task_processor.show_task_details,
                inputs=[
                    components['product_file'], components['packaging_file'], 
                    components['description_file'], components['supplement'],
                    components['image_tiling_algorithm'], components['ai_model'],
                    components['toy_types_input'], components['features_input'],
                    components['sub_features_input'], components['age_from_input'],
                    components['age_to_input']
                ],
                outputs=[components['submit_result']]
            )
        with gr.Tab("分类信息"):
            gr.Markdown("## 可用的分类选项")
            with gr.Row():
                with gr.Column():
                    gr.Markdown("### 类型")
                    toy_types_text = gr.Textbox(
                        value="\n".join(audit_form_generator.get_toy_types()),
                        lines=len(audit_form_generator.get_toy_types()),
                        interactive=False
                    )
                with gr.Column():
                    gr.Markdown("### 产品特性")
                    features_text = gr.Textbox(
                        value="\n".join(audit_form_generator.get_features()),
                        lines=len(audit_form_generator.get_features()),
                        interactive=False
                    )
            with gr.Row():
                with gr.Column():
                    gr.Markdown("### 细分特性")
                    sub_features_text = gr.Textbox(
                        value="\n".join(audit_form_generator.get_sub_features()),
                        lines=len(audit_form_generator.get_sub_features()),
                        interactive=False
                    )
        
        with gr.Tab("审核结果"):
            gr.Markdown("## 审核结果展示")
            review_result_tab.create_ui()

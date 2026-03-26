import os
import gradio as gr
from typing import List, Tuple, Optional
from gradio import File, Request
class TaskProcessor:
    def __init__(self, audit_form_generator):
        self.audit_form_generator = audit_form_generator
    
    def start_recognition(self, 
                         product_files: List[File], 
                         packaging_files: List[File], 
                         description_files: List[File],
                         supplement: str, 
                         image_tiling_algorithm: bool, 
                         ai_model: str, 
                         request: Request) -> Tuple[str, gr.update, gr.update, gr.update, 
                                                   gr.update, gr.update, gr.update, 
                                                   gr.update, gr.update, gr.update, 
                                                   gr.update, gr.update, gr.update]:

        if not product_files and not packaging_files and not description_files:
            return ("请至少上传一个文件", gr.update(), gr.update(), gr.update(), 
                    gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), 
                    gr.update(), gr.update(), gr.update(), gr.update())
        
        # 模拟识别结果
        result_text = f"识别完成！\n产品文件: {len(product_files) if product_files else 0} 个\n包装文件: {len(packaging_files) if packaging_files else 0} 个\n说明书: {len(description_files) if description_files else 0} 个"
        
        # 返回更新后的UI状态
        return (
            result_text,  # output
            gr.update(visible=True, value=["Aquatic Toys"]),  # toy_types_input
            gr.update(visible=True, value=["small part（测试年龄3-6岁）"]),  # features_input
            gr.update(visible=True, value=[]),  # sub_features_input
            gr.update(visible=True),  # age_from_label
            gr.update(visible=True, value="3"),  # age_from_input
            gr.update(visible=True),  # age_from_unit
            gr.update(visible=True),  # age_to_label
            gr.update(visible=True, value="6"),  # age_to_input
            gr.update(visible=True),  # age_to_unit
            gr.update(visible=True)   # submit_btn
        )
    
    def show_task_details(self, 
                         product_files: List[File], 
                         packaging_files: List[File], 
                         description_files: List[File],
                         supplement: str, 
                         image_tiling_algorithm: bool, 
                         ai_model: str,
                         toy_category: List[str], 
                         features: List[str], 
                         sub_features: List[str], 
                         age_from: str, 
                         age_to: str,
                         request: Request) -> gr.update:
        md = f"""
| 项目             | 内容 |
|------------------|------|
| **任务ID**       | {request.session_hash} |
| **产品文件**     | {', '.join([os.path.basename(f.name) for f in product_files]) if product_files else '未上传'} |
| **包装文件**     | {', '.join([os.path.basename(f.name) for f in packaging_files]) if packaging_files else '未上传'} |
| **说明书**       | {', '.join([os.path.basename(f.name) for f in description_files]) if description_files else '未上传'} |
| **补充说明**     | {supplement} |
| **是否使用分图算法** | {image_tiling_algorithm} |
| **AI模型**       | {ai_model} |
| **玩具类别**     | {', '.join(toy_category) if toy_category else '未选择'} |
| **产品特性**     | {', '.join(features) if features else '未选择'} |
| **细分特性**     | {', '.join(sub_features) if sub_features else '未选择'} |
| **设计年龄**     | {age_from} 到 {age_to} |
"""
        return gr.update(value=md, visible=True) 
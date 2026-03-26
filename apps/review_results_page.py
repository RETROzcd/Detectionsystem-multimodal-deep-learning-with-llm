import gradio as gr

def create_review_row(check_item):
    """为每个审核项创建一个Gradio行"""
    with gr.Row(equal_height=False):
        with gr.Column(scale=3, elem_classes=["bg-light-blue"]):
            gr.Markdown(f"**{check_item['description']}**")
        
        with gr.Column(scale=3):
            with gr.Row():
                gr.Image(value=None, label="证据 1", height=37, width=10, interactive=False)
            with gr.Row():
                gr.Image(value=None, label="证据 2", height=37, width=37, interactive=False)

        with gr.Column(scale=3, elem_classes=["bg-light-green"]):
            gr.Markdown(f"**模型结论:** {check_item['ai_conclusion']}")
            gr.Markdown(f"_{check_item['ai_rule']}_")
        
        with gr.Column(scale=3, elem_classes=["bg-light-yellow"]):
            gr.Checkbox(label="错误")
            gr.Textbox(placeholder="请输入正确结论", lines=2, show_label=False)
            gr.Textbox(placeholder="输入错误说明", lines=2, show_label=False)

def build_review_results_page():
    """构建完整的审核结果页面"""
    
    task_details = {
        "left_column": """
        **切图算法**: 是
        <br>
        **玩具类别**: Stuffing toys / Stuffed toys
        <br>
        **产品特性**: Small part (测试年龄3-6岁), Toys intended to be assembled by an adult
        <br>
        **细分特性**: 可更换电池, 电池驱动的玩具, 组装前有小部件，且年龄: 3岁以下, 纽扣电池或硬币电池
        """,
        "right_column": """
        **使用模型**: GPT 4o
        <br>
        **补充说明**: -
        <br>
        **备注**: 12345
        """
    }

    regulation_details = {
        "F.P. & L. Act (16 CFR 500) OR NIST Uniform Laws and Regulations Handbook 130": "这是 **F.P. & L. Act (16 CFR 500) OR NIST Uniform Laws and Regulations Handbook 130** 的具体要求内容。 \n\n * 详细说明1 \n * 详细说明2 \n * 详细说明3",
        "19 CFR 134": "这是 **19 CFR 134** 的具体要求内容。 \n\n * 详细说明A \n * 详细说明B \n * 详细说明C",
        "ASTM F963-23 Clause 5.2": "这是 **ASTM F963-23 Clause 5.2** 的具体要求内容。 \n\n * 详细说明X \n * 详细说明Y \n * 详细说明Z"
    }

    review_data = [
        {
            "chapter": "章节 01 General Labeling requirements",
            "items": [
                {
                    "title": "One Time Use Products Fair Packaging and Labeling Act or All Other Products. Uniform Packaging and Labeling Regulations",
                    "regulation": "F.P. & L. Act (16 CFR 500) OR NIST Uniform Laws and Regulations Handbook 130",
                    "checks": [
                        {
                            "description": "包装上含有制造商、分销商、品牌名称三个中的任意一个，不检查名称真实性，只需要有即可。",
                            "ai_conclusion": "Pass, 因为包装上有制造商名称。",
                            "ai_rule": "规则: if 识别, remark识别的净含量, 提醒需要核实真实净含量. If 只标识了个数, 没有精确净含量, 或者没有标识个数和精确净含量, then Fail"
                        },
                        {
                            "description": "包装上是否有制造商或者分销商的通讯地址",
                            "ai_conclusion": "Pass, 因为包装上有制造商通讯地址。",
                            "ai_rule": "规则: if 识别, remark识别的净含量, 提醒需要核实真实净含量. If 只标识了个数, 没有精确净含量, 或者没有标识个数和精确净含量, then Fail"
                        },
                        {
                            "description": "包装的主展示面上有产品的具体数量、质量、组合方式",
                            "ai_conclusion": "Pass, 因为包装主展示面上有产品数量。",
                            "ai_rule": "规则: if 识别, remark识别的净含量, 提醒需要核实真实净含量. If 只标识了个数, 没有精确净含量, 或者没有标识个数和精确净含量, then Fail"
                        },
                        {
                            "description": "包装的主展示面上是否有产品的名称, 或者描述产品的图片",
                            "ai_conclusion": "Pass, 因为包装主展示面上有产品名称。",
                            "ai_rule": "规则: if 识别, remark识别的净含量, 提醒需要核实真实净含量. If 只标识了个数, 没有精确净含量, 或者没有标识个数和精确净含量, then Fail"
                        }
                    ]
                },
                {
                    "title": "Country of Origin Marking",
                    "regulation": "19 CFR 134",
                    "checks": [
                        {
                            "description": "包装上是否有原产国标记?",
                            "ai_conclusion": "Pass, 因为包装上有原产国标记。",
                            "ai_rule": "规则: if 识别, remark识别的净含量, 提醒需要核实真实净含量. If 只标识了个数, 没有精确净含量, 或者没有标识个数和精确净含量, then Fail"
                        }
                    ]
                }
            ]
        },
        {
            "chapter": "章节 02 General Labeling requirements in toys standards",
            "items": [
                {
                    "title": "Age Grading",
                    "regulation": "ASTM F963-23 Clause 5.2",
                    "checks": [
                        {
                            "description": "包装上是否有表明其产品适用年龄的标识",
                            "ai_conclusion": "Pass, 因为包装上有适用年龄标记。",
                            "ai_rule": "规则: if 识别, remark识别的净含量, 提醒需要核实真实净含量. If 只标识了个数, 没有精确净含量, 或者没有标识个数和精确净含量, then Fail"
                        }
                    ]
                }
            ]
        }
    ]

    modal_css = """
    #modal-container {
        position: fixed !important;
        top: 50% !important;
        left: 50% !important;
        transform: translate(-50%, -50%) !important;
        background: white;
        padding: 2em;
        border-radius: 0.5em;
        box-shadow: 0 4px 8px rgba(0,0,0,0.2);
        z-index: 1000;
        width: 60%;
        max-width: 800px;
    }
    """

    with gr.Blocks(title="SGS玩具标签审核验证平台", theme=gr.themes.Soft(), css=modal_css) as demo:
        gr.Markdown("# SGS玩具标签审核验证平台")

        with gr.Group(visible=False, elem_id="modal-container") as modal_group:
            with gr.Column():
                modal_content = gr.Markdown()
                gr.Button("关闭").click(lambda: gr.update(visible=False), None, modal_group)

        with gr.Row():
            create_task_btn = gr.Button("创建任务", variant="primary")
            rule_library_btn = gr.Button("规则库", variant="secondary")

        with gr.Column(visible=True) as create_task_page:
            with gr.Group():
                gr.Markdown("## 任务详情")
                with gr.Row():
                    with gr.Column(scale=1):
                        gr.Markdown(task_details["left_column"])
                    with gr.Column(scale=1):
                        gr.Markdown(task_details["right_column"])
            
            gr.Markdown("---")
            gr.Markdown("## 审核结果")

            with gr.Tab("审核结果"):
                result_content = gr.Column(visible=False)

            gr.Button("勘误完成, 生成数据", variant="primary", size="lg")

        with gr.Column(visible=False) as rule_library_page:
            gr.Markdown("## 规则库")
            gr.Markdown("这里是规则库的内容。")

        def switch_to_create_task():
            return {
                create_task_page: gr.update(visible=True), 
                rule_library_page: gr.update(visible=False), 
                create_task_btn: gr.update(variant="primary"), 
                rule_library_btn: gr.update(variant="secondary")
            }

        def switch_to_rule_library():
            return {
                create_task_page: gr.update(visible=False), 
                rule_library_page: gr.update(visible=True), 
                create_task_btn: gr.update(variant="secondary"), 
                rule_library_btn: gr.update(variant="primary")
            }

        create_task_btn.click(
            switch_to_create_task, 
            None, 
            [create_task_page, rule_library_page, create_task_btn, rule_library_btn]
        )
        rule_library_btn.click(
            switch_to_rule_library, 
            None, 
            [create_task_page, rule_library_page, create_task_btn, rule_library_btn]
        )

    return demo

if __name__ == "__main__":
    app = build_review_results_page()
    app.launch() 
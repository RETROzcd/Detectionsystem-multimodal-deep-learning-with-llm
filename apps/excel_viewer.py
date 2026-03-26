import gradio as gr
import pandas as pd
import openpyxl
from openpyxl.utils.dataframe import dataframe_to_rows
import io

def process_excel(file):
    if file is None:
        return None
    
    # 读取Excel文件
    wb = openpyxl.load_workbook(file.name)
    sheet = wb.active
    
    # 获取合并单元格信息
    merged_cells = sheet.merged_cells.ranges
    
    # 将Excel转换为DataFrame
    data = []
    for row in sheet.rows:
        row_data = []
        for cell in row:
            # 检查单元格是否在合并区域内
            is_merged = False
            for merged_range in merged_cells:
                if cell.coordinate in merged_range:
                    is_merged = True
                    # 获取合并区域的值
                    value = sheet.cell(merged_range.start_cell.row, merged_range.start_cell.column).value
                    row_data.append(value)
                    break
            if not is_merged:
                row_data.append(cell.value)
        data.append(row_data)
    
    # 创建DataFrame
    df = pd.DataFrame(data)
    
    # 返回HTML表格
    return df.to_html(classes='table table-striped', index=False)

# 创建Gradio界面
with gr.Blocks(title="Excel查看器") as demo:
    gr.Markdown("# Excel文件查看器")
    gr.Markdown("上传Excel文件，支持合并单元格的显示")
    
    with gr.Row():
        file_input = gr.File(label="上传Excel文件", file_types=[".xlsx", ".xls"])
    
    with gr.Row():
        output = gr.HTML(label="Excel内容")
    
    file_input.change(
        fn=process_excel,
        inputs=[file_input],
        outputs=[output]
    )

if __name__ == "__main__":
    demo.launch(share=True) 
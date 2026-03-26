import gradio as gr
import os
import openpyxl
import pandas as pd
from redis_utils import MemoryStorageUtil as RedisUtil
from redis_data import RedisData
class RuleLibraryTab:
    #DEFAULT_EXCEL_PATH = ""
    def __init__(self, redis_util: RedisUtil):
        self.redis_util = redis_util
        self.components = {}
    def create_ui(self) -> gr.Tab:
        with gr.Tab("规则库") as rule_tab:
            self._create_rule_library_components()
            self._setup_event_handlers()
        return rule_tab
    def _create_rule_library_components(self):
        with gr.Row():
            self.components['file_input'] = gr.File(
                label="导入规则",
                file_types=[".xlsx", ".xls"],
                value=self.DEFAULT_EXCEL_PATH if os.path.exists(self.DEFAULT_EXCEL_PATH) else None
            )
        with gr.Row():
            self.components['output'] = gr.HTML(label="Excel内容")
    def _setup_event_handlers(self):
        self.components['file_input'].change(
            fn=self.process_excel,
            inputs=[self.components['file_input']],
            outputs=[self.components['output']]
        )
    def process_excel(self, file, request: gr.Request):
        if file is None:
            return None
        wb = openpyxl.load_workbook(file.name)
        sheet = wb.active
        merged_cells = sheet.merged_cells.ranges
        data = []
        for row in sheet.rows:
            row_data = []
            for cell in row:
                is_merged = False
                for merged_range in merged_cells:
                    if cell.coordinate in merged_range:
                        is_merged = True
                        value = sheet.cell(merged_range.start_cell.row, merged_range.start_cell.column).value
                        row_data.append(value)
                        break
                if not is_merged:
                    row_data.append(cell.value)
            data.append(row_data)
        df = pd.DataFrame(data)
        work_dir = f"./work_dir/{request.session_hash}"
        if not os.path.exists(work_dir):
            os.makedirs(work_dir)
        import shutil
        excel_filename = os.path.basename(file.name)
        destination_path = os.path.join(work_dir, excel_filename)
        shutil.copy2(file.name, destination_path)
        if self.redis_util.exists_key(request.session_hash):
            redis_data = self.redis_util.get_value(request.session_hash)
            redis_data.rule_file_path = destination_path
            self.redis_util.set_value(request.session_hash, redis_data)
        else:
            redis_data = RedisData()
            redis_data.rule_file_path = destination_path
            self.redis_util.set_value(request.session_hash, redis_data)
        return df.to_html(classes='table table-striped', index=False)
    def show_default_excel(self, request: gr.Request):
        if self.redis_util.exists_key(request.session_hash):
            redis_data = self.redis_util.get_value(request.session_hash)
            if redis_data.rule_file_path:
                return self.process_excel(redis_data.rule_file_path, request)
        if os.path.exists(self.DEFAULT_EXCEL_PATH):
            class DummyFile:
                def __init__(self, path):
                    self.name = path
            return self.process_excel(DummyFile(self.DEFAULT_EXCEL_PATH), request)
        else:
            return "未找到默认Excel文件"

    def get_components(self):
        return self.components 
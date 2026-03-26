# -*- coding: utf-8 -*-
import gradio as gr
import shutil
import logging
import os
import sys
import pandas as pd
import openpyxl
from fastapi import FastAPI
from starlette.middleware.sessions import SessionMiddleware
import uuid
import traceback
from gradio import State
import time
import json

# 添加项目根目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.insert(0, project_root)
sys.path.insert(0, current_dir)  # 添加apps目录到路径

from agents.data_preprocess import DataPreprocess
from agents.image_cut.image_cut_agent import ImageCutAgent
from agents.image_cut.image_cut_request import ImageCutRequest
from agents.agent_utils import CutType, ImageType
from agents.object_classify.object_classify_agent import ObjectClassifyAgent
from agents.object_classify.object_classify_request import ObjectClassifyRequest
from agents.rule_check.rule_check_agent import RuleCheckAgent
from agents.rule_check.rule_check_request import RuleCheckRequest
from agents.rule_check.rule_check_response import RuleCheckResponse
from agents.test_all import read_rules
from agents.rule_check.rule import Rule
from agents.rule_check.rule_check_result import RuleCheckResult
from result_excel_generator import ExcelGenerator
from redis_utils import MemoryStorageUtil as RedisUtil, MemoryStorageUtil
from redis_data import RedisData, RedisRuleCheckResult, RedisCategoryAndFeatureData
from utils.excel_name_generator import create_excel_name_generator
from db_utils import DBClient
import uvicorn
import logging
from image_segment_html_generator import ImageSegmentHtmlGenerator
import time

logging.basicConfig(
    level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s', handlers=[logging.FileHandler("./logs/create_orders_page.log"), logging.StreamHandler()],
    force=True
)
logging.getLogger("httpx").setLevel(logging.WARNING)

#DEFAULT_EXCEL_PATH = ""

object_classify_gpt_config = {
    "gpt-4o": {
        "prompt_version": "",
        "model_name": "",
        "api_key": "",
        "api_version": "",
        "azure_endpoint": "",
        "max_image_size": 2048
    },
    "gpt-5": {
    },
    "o4-mini": {
    },
     "qwen-vl-max": {
    },
    "doubao-seed": {
    }
}
model_config =  {
    "preprocess_configs": {"supported_filetype": {"pdf", "jpg", "png", "jpeg"}},
    "image_cut_configs": {   
        "enable_vlm_cut": True,
        "enable_ocr_cut": False,
        "enable_sam_cut": False,
        "sam_model_name": "FastSAM",
        "sam_model_ckpt": "./models/FastSAM-s.pt",
        "sam_device_id": "cpu",
        "sam_max_size": 512,
        "sam_conf": 0.15,
        "sam_iou": 0.5,
        "sam_occupy_ratio": 0.35,
        "ocr_sam_iou_threshold": 0.1,
        "model_input_image_size": (768, 768),
        "cut_mode": CutType.PER_BOUNDING_BOX,
        "vlm_cut_model_configs": {

        }
    },
    "rule_check_configs":  {
        "check_necessity_prompt_version": "",
        "check_mode": "",
        "check_passthrough_prompt_version": "",
        "image_keyword_extract_prompt_version": "",
        "merged_rule_check_prompt_version": "",
        "model_name": "",

        "max_workers": 12
        }
}

redis_util = MemoryStorageUtil()
db_client = DBClient()
excel_name_generator = create_excel_name_generator(redis_util)
app = FastAPI()
app.add_middleware(
    SessionMiddleware, 
    secret_key=""
)


def process_form(product_file, packaging_file, description_file, supplement, image_tiling_algorithm, ai_model, toy_types, features, sub_features, age_from, age_to):
    return f"""
产品文件: {product_file.name if product_file else '未上传'}\n包装文件: {packaging_file.name if packaging_file else '未上传'}\n说明书: {description_file.name if description_file else '未上传'}\n补充说明: {supplement}\n识别模型提示词: {image_tiling_algorithm}\nAI模型: {ai_model}\n玩具类别: {', '.join(toy_types) if toy_types else '未选择'}\n产品特性: {', '.join(features) if features else '未选择'}\n细分特性: {', '.join(sub_features) if sub_features else '未选择'}\n设计年龄: {age_from} 到 {age_to} 岁
"""

def process_excel(file, request: gr.Request):
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
    df = pd.DataFrame(data).fillna("")
    if not os.path.exists(f"./work_dir/{request.session_hash}"):
        os.makedirs(f"./work_dir/{request.session_hash}")
    import shutil
    excel_filename = os.path.basename(file.name)
    destination_path = os.path.join(f"./work_dir/{request.session_hash}", excel_filename)
    if file.name != destination_path:
        shutil.copy2(file.name, destination_path)

    if redis_util.exists_key(request.session_hash):
        redis_data = redis_util.get_value(request.session_hash)
        redis_data.rule_file_path = destination_path
        redis_util.set_value(request.session_hash, redis_data)
    else:
        redis_data = RedisData()
        redis_data.rule_file_path = destination_path
        redis_util.set_value(request.session_hash, redis_data)

    table_html = df.to_html(classes='table table-striped', index=False, escape=True)
    return f'<div class="rule-parse-table-wrapper">{table_html}</div>'

def preprocess(product_files, packaging_files, description_files, supplement, image_tiling_algorithm, ai_model, request: gr.Request):
    print(f"Final task_id: {request.session_hash}")
    if not product_files and not packaging_files and not description_files:
        return (False, "请至少上传一个文件")
    print(f"product_file: {product_files}")
    print(f"packaging_file: {packaging_files}")
    print(f"description_file: {description_files}")
    print(f"supplement: {supplement}")
    print(f"image_tiling_algorithm: {image_tiling_algorithm}")
    print(f"ai_model: {ai_model}")
    enable_cut_images = image_tiling_algorithm == "是"
    # 数据预处理
    if redis_util.exists_key(request.session_hash):
        redis_data = redis_util.get_value(request.session_hash)
    else:
        redis_data = RedisData()

    if not os.path.exists(f"./work_dir/{request.session_hash}"):
        os.makedirs(f"./work_dir/{request.session_hash}")
    # 创建目录并复制文件
    gradio_image_directories = {
        "product_images": product_files if product_files else [],
        "package_images": packaging_files if packaging_files else [],
        "manual_images": description_files if description_files else [],
    }
    work_dir_image_directories = {
        "product_images": [],
        "package_images": [],
        "manual_images": [],
    }
    
    for dir_name, files in gradio_image_directories.items():
        dir_path = f"./work_dir/{request.session_hash}/{dir_name}"
        if os.path.exists(dir_path):
            try:
                shutil.rmtree(dir_path)
            except PermissionError as e:
                logging.warning(f"rmtree failed for {dir_path}, ignore and reuse existing dir: {e}")
        os.makedirs(dir_path, exist_ok=True)
        for file in files:
            if file:
                dst = f"{dir_path}/{os.path.basename(file.name)}"
                try:
                    shutil.copy2(file.name, dst)
                    work_dir_image_directories[dir_name].append(dst)
                except PermissionError as e:
                    logging.warning(f"copy2 failed for {file.name} -> {dst}, skip this file: {e}")
    logging.info(f"work_dir_image_directories: {work_dir_image_directories}")
    logging.info(f"gradio_image_directories: {gradio_image_directories}")
    dp = DataPreprocess(model_config["preprocess_configs"])
    redis_data.user_input_data = {
        "task_id": request.session_hash,
        "product_images": work_dir_image_directories["product_images"],
        "package_images": work_dir_image_directories["package_images"],
        "manual_images": work_dir_image_directories["manual_images"],
        "work_dir": os.path.join("./work_dir"),
        "other_info": supplement if supplement else "",
        }
    redis_data.preprocessed_data = dp.process(redis_data.user_input_data)
    logging.info(f"preprocessed_data: {redis_data.preprocessed_data}")




    if enable_cut_images:
        image_cut_agent = ImageCutAgent(model_config["image_cut_configs"])
        image_cut_request = ImageCutRequest(task_id=redis_data.user_input_data["task_id"], 
                                        product_images=redis_data.preprocessed_data[ImageType.PRODUCT] if ImageType.PRODUCT in redis_data.preprocessed_data else [], 
                                        package_images=redis_data.preprocessed_data[ImageType.PACKAGE] if ImageType.PACKAGE in redis_data.preprocessed_data else [], 
                                        manual_images=redis_data.preprocessed_data[ImageType.MANUAL] if ImageType.MANUAL in redis_data.preprocessed_data else [], 
                                        work_dir=redis_data.preprocessed_data["work_dir"])
        redis_data.image_cut_response = image_cut_agent.cut_images(image_cut_request)
        logging.info(f"image_cut_response: {redis_data.image_cut_response}")





    redis_data.toy_category = []
    redis_data.object_classify_response = None
    redis_util.set_value(request.session_hash, redis_data)
    if True:
        try:
            package_images4classify = []
            if ImageType.PACKAGE in redis_data.preprocessed_data and len(redis_data.preprocessed_data[ImageType.PACKAGE]) > 0:
                processed2original_map = redis_data.preprocessed_data["processed2original_map"]
                for source_data in redis_data.preprocessed_data[ImageType.PACKAGE]:
                    original_path = processed2original_map[source_data]
                    if original_path.endswith(".pdf") and enable_cut_images and redis_data.image_cut_response is not None:
                        cutted_package_image_map = redis_data.image_cut_response.get_cutted_package_images()
                        if source_data in cutted_package_image_map and cutted_package_image_map[source_data] is not None and len(cutted_package_image_map[source_data]) > 0:
                            package_images4classify.extend(cutted_package_image_map[source_data])
                        else:
                            package_images4classify.append(source_data)
                    else:
                        package_images4classify.append(source_data)
            else:
                package_images4classify = redis_data.preprocessed_data[ImageType.PACKAGE] if ImageType.PACKAGE in redis_data.preprocessed_data else []

            object_classify_agent = ObjectClassifyAgent(object_classify_gpt_config[ai_model])
            product_imgs = list(redis_data.preprocessed_data[ImageType.PRODUCT]) if ImageType.PRODUCT in redis_data.preprocessed_data else []
            package_imgs = list(package_images4classify)
            manual_imgs = list(redis_data.preprocessed_data[ImageType.MANUAL]) if ImageType.MANUAL in redis_data.preprocessed_data else []
            max_images = 50
            if len(product_imgs) + len(package_imgs) + len(manual_imgs) > max_images:
                remain = max_images - len(product_imgs) - len(package_imgs)
                if remain < 0:
                    combined = product_imgs + package_imgs
                    combined = combined[:max_images]
                    product_imgs = combined[: len(product_imgs)]
                    package_imgs = combined[len(product_imgs) :]
                    manual_imgs = []
                else:
                    manual_imgs = manual_imgs[:remain]
                logging.warning(
                    f"Too many images for object classify, truncate to {max_images}. "
                    f"product={len(product_imgs)}, package={len(package_imgs)}, manual={len(manual_imgs)}"
                )
            object_classify_request = ObjectClassifyRequest(
                task_id=redis_data.user_input_data["task_id"],
                product_images=product_imgs,
                package_images=package_imgs,
                manual_images=manual_imgs,
                other_info=redis_data.user_input_data["other_info"],
            )
            redis_data.object_classify_response = object_classify_agent.classify_object(object_classify_request)
            print(f"object_classify_response: {redis_data.object_classify_response}")
            logging.info(f"object_classify_response: {redis_data.object_classify_response}")
        except Exception as e:
            logging.error(f"object_classify_error: {e}, {traceback.format_exc()}")

        if redis_data.object_classify_response is not None and redis_data.object_classify_response.get_status():
            all_ui_toy = set(PRECONDITION_MODULE_1)
            all_ui_features = set(PRECONDITION_MODULE_3_PHYSICAL + PRECONDITION_MODULE_3_AGE + PRECONDITION_MODULE_3_FUNC + PRECONDITION_MODULE_3_CHEM + PRECONDITION_MODULE_4 + PRECONDITION_MODULE_5)
            redis_data.ai_category_and_feature_data.toy_category = [t for t in redis_data.object_classify_response.get_toy_category() if t in all_ui_toy]
            redis_data.ai_category_and_feature_data.features = [f for f in redis_data.object_classify_response.get_product_features() if f in all_ui_features]
            if not redis_data.ai_category_and_feature_data.toy_category:
                redis_data.ai_category_and_feature_data.toy_category = list(redis_data.object_classify_response.get_toy_category())
            if not redis_data.ai_category_and_feature_data.features:
                redis_data.ai_category_and_feature_data.features = list(redis_data.object_classify_response.get_product_features())

            sub_chem = {"Toxic", "Corrosive", "Irritant", "strong sensitizer", "flammable", "Combustible", "Generate pressure through decomposition", "heat or other means"}
            sub_battery = {"可更换电池的玩具", "不可更换电池的玩具", "纽扣电池或硬币电池驱动的玩具", "带有充电电池", "铅酸充电电池", "镍铬充电电池", "可更换电池", "不可更换电池", "纽扣电池或硬币电池"}
            if "含有化学品并且会产生化学反应的实验套装" in redis_data.ai_category_and_feature_data.toy_category or any("化学" in str(t) for t in redis_data.object_classify_response.get_toy_category()):
                redis_data.ai_category_and_feature_data.sub_features_chemical_experiment_kit_with_reactive_substances = [s for s in redis_data.object_classify_response.get_sub_features() if s in sub_chem or "化学" in str(s)]
            if "电池驱动的玩具" in redis_data.ai_category_and_feature_data.features or any("电池" in str(f) for f in redis_data.object_classify_response.get_product_features()):
                redis_data.ai_category_and_feature_data.sub_features_battery_powered_toy = [s for s in redis_data.object_classify_response.get_sub_features() if s in sub_battery or "电池" in str(s)]

            logging.info(f"redis_data.ai_category_and_feature_data.toy_category: {redis_data.ai_category_and_feature_data.toy_category}")
            logging.info(f"redis_data.ai_category_and_feature_data.features: {redis_data.ai_category_and_feature_data.features}")
            logging.info(f"redis_data.ai_category_and_feature_data.sub_features_chemical_experiment_kit_with_reactive_substances: {redis_data.ai_category_and_feature_data.sub_features_chemical_experiment_kit_with_reactive_substances}")
            logging.info(f"redis_data.ai_category_and_feature_data.sub_features_battery_powered_toy: {redis_data.ai_category_and_feature_data.sub_features_battery_powered_toy}")

    redis_data.work_dir_image_directories = work_dir_image_directories
    redis_util.set_value(request.session_hash, redis_data)

    return (True, "")

# 玩具合规选项：5 个模块，共 8 组 CheckboxGroup（模块3 拆成 4 个子组）
PRECONDITION_MODULE_1 = [  # 前置条件与产品类型
    "水上运动玩具", "婴儿床和游戏围栏玩具", "婴儿车和手推车玩具", "模拟防护装置", "磁性/电气实验套装",
    "接触食品的玩具", "玩具箱", "美术材料", "填充玩具/毛绒玩具",
    "服装、手帕、围巾、袜子及针织品（纤维成分）", "纺织品服装不包含配件（护理标签）", "含有复合木(CARB)",
    "含有复合木（复合木面积大于等于144平方英寸 TSCA）", "化妆品玩具"
]
PRECONDITION_MODULE_2 = [  # 适用合规类型
    "适用UPLR（非消耗品）", "适用FPLA和UPLR中的消耗品"
]
PRECONDITION_MODULE_3_PHYSICAL = [  # 核心风险特征 - 物理安全风险
    "小部件", "小球", "弹珠", "乳胶气球", "骑乘玩具", "带可更换保险丝或电路保护的骑乘玩具"
]
PRECONDITION_MODULE_3_AGE = [  # 核心风险特征 - 年龄与结构风险
    "需由成人组装的玩具", "组装前有小部件且年龄：3岁以下", "有尖点利边且年龄：0-8岁",
    "悬挂玩具", "悬挂玩具（附着于婴儿床、游戏围栏、墙或天花板）", "悬挂玩具（仅附着于墙或天花板）"
]
PRECONDITION_MODULE_3_FUNC = [  # 核心风险特征 - 功能风险
    "带功能锐边玩具", "带功能尖点玩具", "带功能锐边和尖点玩具"
]
PRECONDITION_MODULE_3_CHEM = [  # 核心风险特征 - 化学与压力风险
    "含有化学品并且会产生化学反应的实验套装",
    "有毒或腐蚀性或刺激性或强致敏性或易燃或可燃，或通过分解/热等产生压力",
    "含有配置品（液体，粉末，油灰，糊剂，凝胶）", "有加压容器"
]
PRECONDITION_MODULE_4 = [  # 无线与认证合规
    "无线产品（例如27 MHz，49 MHz）、WIFI或蓝牙产品", "SAR标识(备注1)", "SAR标识(备注2)", "FCC屏蔽电缆",
    "非有意发射的B/O玩具大于1.705Hz；或变压器充电/供电；或USB供电；或有意发射玩具的接收器（比如遥控车）；或通过插头接市电且频率大于等于9KHz的产品",
    "电池充电器（包括USB充电或者适配器充电等）", "外接电源"
]
PRECONDITION_MODULE_5 = [  # 电气与电池合规
    "电动玩具（接市电供电正常工作的产品，直接供电的变压器）", "设计不是在水中使用的，但使用过程中有可能接触到水",
    "产品中有可更换的白炽灯", "产品中有不可更换的白炽灯", "电池驱动的玩具", "可更换电池", "电池数量大于等于2",
    "本身含有打开电池盖的特定工具", "通过常用工具可以打开的不可更换电池", "纽扣电池或硬币电池",
    "电池容易移除", "电池不容易移除", "镍铬充电电池", "铅酸充电电池"
]
preconditions = [
    PRECONDITION_MODULE_1,
    PRECONDITION_MODULE_2,
    PRECONDITION_MODULE_3_PHYSICAL,
    PRECONDITION_MODULE_3_AGE,
    PRECONDITION_MODULE_3_FUNC,
    PRECONDITION_MODULE_3_CHEM,
    PRECONDITION_MODULE_4,
    PRECONDITION_MODULE_5,
]

AI_TO_UI_PRECONDITION_MAP = {
    "Aquatic Toys": "水上运动玩具",
    "Crib and Playpen Toys": "婴儿床和游戏围栏玩具",
    "Stroller and Carriage Toys": "婴儿车和手推车玩具",
    "Simulated Protective Devices": "模拟防护装置",
    "Magnetic/electrical experimental sets": "磁性/电气实验套装",
    "Toys in Contact with Food": "接触食品的玩具",
    "Toy Chests": "玩具箱",
    "Art Materials": "美术材料",
    "Stuffing toys / Stuffed toys": "填充玩具/毛绒玩具",
    "服装、手帕、围巾、袜子及针织品（纤维成分）": "服装、手帕、围巾、袜子及针织品（纤维成分）",
    "纺织品服装不包含配件（护理标签）": "纺织品服装不包含配件（护理标签）",
    "Clothing，Handkerchiefs，Scarfs，socks  and hoisery": "服装、手帕、围巾、袜子及针织品（纤维成分）",
    "含有复合木(CARB)": "含有复合木(CARB)",
    "含有复合木（复合木面积大于等于144平方英寸 TSCA）": "含有复合木（复合木面积大于等于144平方英寸 TSCA）",
    "化妆品玩具": "化妆品玩具",
    "含有化学品并且会产生化学反应的实验套装": "含有化学品并且会产生化学反应的实验套装",
    "Ride-on Toys": "骑乘玩具",
    "Electric Toys": "电动玩具（接市电供电正常工作的产品，直接供电的变压器）",
    "小部件": "小部件",
    "small part（测试年龄为3-6岁）": "小部件",
    "小球": "小球",
    "small ball": "小球",
    "弹珠": "弹珠",
    "Marbles": "弹珠",
    "乳胶气球": "乳胶气球",
    "Latex balloons": "乳胶气球",
    "需由成人组装的玩具": "需由成人组装的玩具",
    "Toys Intended to be assembled by an adult": "需由成人组装的玩具",
    "组装前有小部件，且玩具适用年龄：3岁以下": "组装前有小部件且年龄：3岁以下",
    "组装前有小部件且年龄：3岁以下": "组装前有小部件且年龄：3岁以下",
    "有尖点利边，且玩具适用年龄：0-8岁": "有尖点利边且年龄：0-8岁",
    "有尖点利边且年龄：0-8岁": "有尖点利边且年龄：0-8岁",
    "悬挂玩具": "悬挂玩具",
    "Mobiles": "悬挂玩具（附着于婴儿床、游戏围栏、墙或天花板）",
    "带功能锐边玩具": "带功能锐边玩具",
    "带功能尖点玩具": "带功能尖点玩具",
    "带功能锐边和尖点玩具": "带功能锐边和尖点玩具",
    "Toys with Functional Sharp Edges or Points": "带功能锐边和尖点玩具",
    "有毒或腐蚀性或刺激性或强致敏性或易燃或可燃，或通过分解/热等产生压力": "有毒或腐蚀性或刺激性或强致敏性或易燃或可燃，或通过分解/热等产生压力",
    "含有配置品（液体，粉末，油灰，糊剂，凝胶）": "含有配置品（液体，粉末，油灰，糊剂，凝胶）",
    "含有配置品（液体，粉末，油灰，糊剂，凝胶）的玩具": "含有配置品（液体，粉末，油灰，糊剂，凝胶）",
    "有加压容器": "有加压容器",
    "有加压容器的玩具": "有加压容器",
    "无线产品（例如27 MHz，49 MHz）、WIFI或蓝牙产品": "无线产品（例如27 MHz，49 MHz）、WIFI或蓝牙产品",
    "无线产品（例如27 MHz，49 MHz),WIFI或者蓝牙产品": "无线产品（例如27 MHz，49 MHz）、WIFI或蓝牙产品",
    "非有意发射的B/O玩具大于1.705Hz；或变压器充电/供电；或USB供电；或有意发射玩具的接收器（比如遥控车）；或通过插头接市电且频率大于等于9KHz的产品": "非有意发射的B/O玩具大于1.705Hz；或变压器充电/供电；或USB供电；或有意发射玩具的接收器（比如遥控车）；或通过插头接市电且频率大于等于9KHz的产品",
    "电池驱动的玩具": "电池驱动的玩具",
    "设计不是在水中使用的，但使用过程中有可能接触到水": "设计不是在水中使用的，但使用过程中有可能接触到水",
    "设计不是在水中使用的, 但是使用过程中有可能接触到水的玩具": "设计不是在水中使用的，但使用过程中有可能接触到水",
    "可更换电池": "可更换电池",
    "可更换电池的玩具": "可更换电池",
    "纽扣电池或硬币电池": "纽扣电池或硬币电池",
    "纽扣电池或硬币电池驱动的玩具": "纽扣电池或硬币电池",
    "铅酸充电电池": "铅酸充电电池",
    "镍铬充电电池": "镍铬充电电池",
    "本身含有打开电池盖的特定工具": "本身含有打开电池盖的特定工具",
    "本身含有打开电池盖的特定工具的玩具": "本身含有打开电池盖的特定工具",
    "产品中有可更换的白炽灯": "产品中有可更换的白炽灯",
    "产品中有不可更换的白炽灯": "产品中有不可更换的白炽灯",
    "产品中有白炽灯的玩具": "产品中有可更换的白炽灯",
    "适用UPLR（非消耗品）": "适用UPLR（非消耗品）",
    "适用UPLR": "适用UPLR（非消耗品）",
    "适用FPLA和UPLR中的消耗品": "适用FPLA和UPLR中的消耗品",
}

def _classification_to_precondition_values(object_classify_response):
    if object_classify_response is None or not object_classify_response.get_status():
        return None
    toy_cat = set(object_classify_response.get_toy_category() or [])
    prod_f = set(object_classify_response.get_product_features() or [])
    sub_f = set(object_classify_response.get_sub_features() or [])
    all_ai_terms = toy_cat | prod_f | sub_f
    ui_terms = set()
    for t in all_ai_terms:
        ui_terms.add(AI_TO_UI_PRECONDITION_MAP.get(t, t))
    ui_terms |= all_ai_terms  # 保留原样也可能匹配
    result = []
    for opts in preconditions:
        selected = [o for o in opts if o in ui_terms]
        result.append(selected)
    return result

with gr.Blocks(
    css="""
.bordered-component {
    border: 2px solid #e0e0e0 !important;
    border-radius: 8px !important;
    padding: 10px !important;
    margin: 5px 0 !important;
}
.section-card {
    border: 1px solid #e2e8f0 !important;
    border-radius: 12px !important;
    padding: 16px 20px !important;
    margin: 12px 0 !important;
    background: #f8fafc !important;
    box-shadow: 0 1px 3px rgba(0,0,0,0.06) !important;
}
.tutorial-box {
    border-left: 4px solid #3b82f6 !important;
    background: #eff6ff !important;
    padding: 14px 18px !important;
    margin: 12px 0 !important;
    border-radius: 0 8px 8px 0 !important;
    font-size: 0.95em !important;
}
.tutorial-box h4 { margin: 0 0 8px 0 !important; color: #1e40af !important; }
.tutorial-box, .tutorial-box * { color: #1e40af !important; }
.tutorial-box ul { margin: 6px 0 !important; padding-left: 20px !important; }
.tutorial-box li { margin: 4px 0 !important; }
.subtab-label { font-weight: 600 !important; color: #334155 !important; }

.usage-instruction, .usage-instruction * { color: #ffffff !important; }

#main-tabs {
    width: 100% !important;
    display: flex !important;
    justify-content: center !important;
}
#main-tabs > div:first-child,
#main-tabs .tabs {
    display: flex !important;
    justify-content: center !important;
    flex-wrap: wrap !important;
}
#main-tabs button {
    font-size: 1.15rem !important;
    padding: 14px 32px !important;
    min-width: 120px !important;
}
.rule-parse-table-wrapper {
    width: 100% !important;
    max-height: min(75vh, 800px) !important;
    overflow: auto !important;
    border: 1px solid #e2e8f0 !important;
    border-radius: 10px !important;
    padding: 12px !important;
    background: #ffffff !important;
    box-shadow: 0 1px 4px rgba(0,0,0,0.06) !important;
    margin-top: 8px !important;
}
.rule-parse-table-wrapper table {
    width: max-content !important;
    min-width: 100% !important;
    border-collapse: collapse !important;
    font-size: 0.875rem !important;
    table-layout: auto !important;
}
.rule-parse-table-wrapper thead {
    position: sticky !important;
    top: 0 !important;
    z-index: 1 !important;
    background: #1e40af !important;
    color: #fff !important;
    box-shadow: 0 2px 2px rgba(0,0,0,0.08) !important;
}
.rule-parse-table-wrapper th {
    padding: 10px 12px !important;
    text-align: left !important;
    font-weight: 600 !important;
    white-space: nowrap !important;
    border: 1px solid #3b82f6 !important;
}
.rule-parse-table-wrapper td {
    padding: 8px 12px !important;
    border: 1px solid #e2e8f0 !important;
    max-width: 320px !important;
    word-wrap: break-word !important;
    overflow-wrap: break-word !important;
    vertical-align: top !important;
    color: #1e40af !important;
}
.rule-parse-table-wrapper tbody,
.rule-parse-table-wrapper tbody * {
    color: #1e40af !important;
}
.rule-parse-table-wrapper tbody tr:nth-child(even) {
    background: #f8fafc !important;
}
.rule-parse-table-wrapper tbody tr:hover {
    background: #eff6ff !important;
}
.rule-parse-output-row { width: 100% !important; }
#rule-parse-output { width: 100% !important; min-height: 200px !important; }

/* 玩具合规选项排版 - 前置条件与设计年龄 */
.compliance-container {
    background-color: #ffffff !important;
    border-radius: 8px !important;
    box-shadow: 0 2px 10px rgba(0,0,0,0.1) !important;
    padding: 24px !important;
    max-width: 1200px !important;
    margin: 0 auto !important;
}
.compliance-module {
    margin-bottom: 24px !important;
    padding-bottom: 16px !important;
    border-bottom: 1px solid #e8e8e8 !important;
}
.compliance-module .module-title {
    font-size: 16px !important;
    font-weight: 600 !important;
    color: #333333 !important;
    margin-bottom: 12px !important;
    display: flex !important;
    align-items: center !important;
    gap: 8px !important;
}
.compliance-module .module-title i {
    color: #1677ff !important;
    font-style: normal !important;
}
/* 选项横向排列，写满一行再换行 */
.compliance-option-grid,
.compliance-option-grid .wrap,
.compliance-option-grid fieldset,
.compliance-option-grid > div {
    display: flex !important;
    flex-wrap: wrap !important;
    gap: 10px 16px !important;
    align-items: center !important;
}
.compliance-option-grid label {
    flex: 0 1 auto !important;
    max-width: 100% !important;
    white-space: normal !important;
}
.compliance-risk-grid {
    display: grid !important;
    grid-template-columns: repeat(2, minmax(280px, 1fr)) !important;
    gap: 12px 20px !important;
}
.compliance-option-item { font-size: 13px !important; color: #333333 !important; }
.compliance-module-type {
    background-color: #f9fafb !important;
    padding: 12px !important;
    border-radius: 6px !important;
}
.compliance-module-risk {
    background-color: #fef2f2 !important;
    padding: 12px !important;
    border-radius: 6px !important;
}
.compliance-module-special {
    background-color: #f0f7ff !important;
    padding: 12px !important;
    border-radius: 6px !important;
}
.compliance-module-cert { padding: 12px !important; border-radius: 6px !important; }
.compliance-risk-item label,
.compliance-risk-item .block { color: #ffffff !important; }
.compliance-risk-item input { accent-color: #d32f2f !important; }
.compliance-group-subtitle {
    font-size: 14px !important; font-weight: 500 !important; color: #d32f2f !important; margin-bottom: 8px !important;
}
@media (max-width: 768px) {
    .compliance-risk-grid { grid-template-columns: 1fr !important; }
}
""",
    title="检测系统",
    theme=gr.themes.Soft(primary_hue="blue", secondary_hue="slate"),
) as demo:
    print(f"demo: {demo}")
    with gr.Tabs(elem_id="main-tabs") as tabs:
        with gr.Tab("规则库") as rule_tab:
            import os
            gr.HTML("""
<div class="tutorial-box">
<h4>📖 规则库使用说明</h4>
<ul>
<li><strong>作用</strong>：规则库是审核所依据的条款来源。系统会按当前规则表对您上传的产品/包装/说明书进行逐条审核。</li>
<li><strong>使用方式</strong>：在「规则表格」子页中上传或选择一份 Excel（.xlsx/.xls）。若未上传，将使用系统默认规则文件。</li>
<li><strong>建议</strong>：首次使用可先不修改规则，直接去「创建任务」上传材料并提交；若需自定义规则，请在此上传符合格式的规则 Excel 后再创建任务。</li>
</ul>
</div>
""")
            with gr.Tabs():
                with gr.Tab("使用说明"):
                    gr.Markdown("""
### 规则文件说明
- **支持格式**：`.xlsx`、`.xls`
- **默认规则**：系统内置默认规则文件，切换至「规则表格」即可查看
- **自定义规则**：上传您自己的 Excel 后，创建任务时将按该规则进行审核
- **流程**：规则库 → 创建任务（上传材料、选前置条件）→ 审核结果
""", elem_classes=["usage-instruction"])
                with gr.Tab("规则解析"):
                    with gr.Row():
                        file_input = gr.File(label="导入规则", file_types=[".xlsx", ".xls"], value=DEFAULT_EXCEL_PATH if os.path.exists(DEFAULT_EXCEL_PATH) else None)
                    with gr.Row(elem_classes=["rule-parse-output-row"]):
                        output = gr.HTML(label="Excel内容", elem_id="rule-parse-output")

            def show_default_excel(request: gr.Request):
                class DummyFile:
                    def __init__(self, path):
                        self.name = path
                if redis_util.exists_key(request.session_hash):
                    redis_data = redis_util.get_value(request.session_hash)
                    if redis_data.rule_file_path:
                        return process_excel(DummyFile(redis_data.rule_file_path), request)
                if os.path.exists(DEFAULT_EXCEL_PATH):
                    return process_excel(DummyFile(DEFAULT_EXCEL_PATH), request)
                else:
                    return "未找到默认Excel文件"

            file_input.change(
                fn=process_excel,
                inputs=[file_input],
                outputs=[output]
            )
            rule_tab.select(
                fn=show_default_excel,
                inputs=[],
                outputs=[output]
            )

        with gr.Tab("创建任务") as create_task_tab:
            gr.HTML("""
<div class="tutorial-box">
<h4>📖 操作步骤</h4>
<ul>
<li><strong>步骤 1</strong>：在本页「步骤1：上传材料」中上传产品图、包装图、说明书（可多选），并填写补充说明（可选）。</li>
<li><strong>步骤 2</strong>：在「步骤2：模型与选项」中选择是否使用切图算法、以及要使用的 AI 模型。</li>
<li><strong>步骤 3</strong>：在「步骤3：前置条件与年龄」中勾选适用的前置条件，填写设计年龄（从/到），最后点击「保存并创建审核表单」。</li>
<li>提交成功后，请点击顶部 <strong>「审核结果」</strong> Tab 查看任务详情与审核结果。</li>
</ul>
</div>
""")
            with gr.Tabs() as create_inner_tabs:
                with gr.Tab("步骤1：上传材料"):
                    gr.Markdown("### 上传材料")
                    with gr.Row():
                        product_file = gr.File(label="产品", file_count="multiple")
                    with gr.Row():
                        packaging_file = gr.File(label="包装", file_count="multiple")
                    with gr.Row():
                        description_file = gr.File(label="说明书", file_count="multiple")
                    supplement = gr.Textbox(label="补充说明", placeholder="可选：填写产品或审核相关的补充说明")
                with gr.Tab("步骤2：模型与选项"):
                    gr.Markdown("### 模型与选项")
                    image_tiling_algorithm = gr.Radio(["否", "是"], label="使用切图算法", value="否")
                    ai_model = gr.Dropdown(["o4-mini", "gpt-4o", "qwen-vl-max", "gpt-5","doubao-seed"], label="选择使用模型", value="o4-mini")
                    start_btn = gr.Button("开始识别", variant="secondary", visible=True)
                with gr.Tab("步骤3：前置条件与年龄"):
                    gr.Markdown("### 前置条件与设计年龄")
                    start_result_md = gr.Markdown("", visible=True)
                    with gr.Column(elem_classes=["compliance-container"]):
                        # 模块1：前置条件与产品类型
                        with gr.Group(elem_classes=["compliance-module", "compliance-module-type"]):
                            gr.HTML('<h3 class="module-title"><i>📦</i>前置条件与产品类型</h3>')
                            p1 = gr.CheckboxGroup(PRECONDITION_MODULE_1, show_label=False, elem_classes=["compliance-option-grid"])
                        # 模块2：适用合规类型
                        with gr.Group(elem_classes=["compliance-module", "compliance-module-special"]):
                            gr.HTML('<h3 class="module-title"><i>📋</i>适用合规类型</h3>')
                            p2 = gr.CheckboxGroup(PRECONDITION_MODULE_2, show_label=False, elem_classes=["compliance-option-grid"])
                        # 模块3：核心风险特征（2x2 子组，与 risk-grid 两列一致）
                        with gr.Group(elem_classes=["compliance-module", "compliance-module-risk"]):
                            gr.HTML('<h3 class="module-title"><i>⚠️</i>核心风险特征</h3>')
                            with gr.Row(elem_classes=["compliance-risk-grid"]):
                                with gr.Column():
                                    gr.HTML('<h4 class="compliance-group-subtitle">物理安全风险</h4>')
                                    p3a = gr.CheckboxGroup(PRECONDITION_MODULE_3_PHYSICAL, show_label=False, elem_classes=["compliance-risk-item"])
                                    gr.HTML('<h4 class="compliance-group-subtitle">年龄与结构风险</h4>')
                                    p3b = gr.CheckboxGroup(PRECONDITION_MODULE_3_AGE, show_label=False, elem_classes=["compliance-risk-item"])
                                with gr.Column():
                                    gr.HTML('<h4 class="compliance-group-subtitle">功能风险</h4>')
                                    p3c = gr.CheckboxGroup(PRECONDITION_MODULE_3_FUNC, show_label=False, elem_classes=["compliance-risk-item"])
                                    gr.HTML('<h4 class="compliance-group-subtitle">化学与压力风险</h4>')
                                    p3d = gr.CheckboxGroup(PRECONDITION_MODULE_3_CHEM, show_label=False, elem_classes=["compliance-risk-item"])
                        # 模块4：无线与认证合规
                        with gr.Group(elem_classes=["compliance-module", "compliance-module-cert"]):
                            gr.HTML('<h3 class="module-title"><i>✅</i>无线与认证合规</h3>')
                            p4 = gr.CheckboxGroup(PRECONDITION_MODULE_4, show_label=False, elem_classes=["compliance-option-grid"])
                        # 模块5：电气与电池合规
                        with gr.Group(elem_classes=["compliance-module", "compliance-module-special"]):
                            gr.HTML('<h3 class="module-title"><i>🔋</i>电气与电池合规</h3>')
                            p5 = gr.CheckboxGroup(PRECONDITION_MODULE_5, show_label=False, elem_classes=["compliance-option-grid"])
                    precondition_boxes = [p1, p2, p3a, p3b, p3c, p3d, p4, p5]
                    with gr.Row():
                        age_from_label = gr.Markdown("#### 设计年龄从", visible=True)
                        age_from_input = gr.Textbox(label="输入框", placeholder="请输入设计年龄从", value="1", visible=True)
                        age_from_unit = gr.Dropdown(["岁", "月"], label="单位", value="岁", visible=True, interactive=True)
                        age_to_label = gr.Markdown("#### 设计年龄到", visible=True)
                        age_to_input = gr.Textbox(label="输入框", placeholder="请输入设计年龄到", value="14", visible=True)
                        age_to_unit = gr.Dropdown(["岁", "月"], label="单位", value="岁", visible=True, interactive=True)
                    submit_btn = gr.Button("保存并创建审核表单", visible=True, variant="primary")
                    submit_result = gr.Markdown("", visible=False)

            def start_recognition(product_files, packaging_files, description_files, supplement, image_tiling_algorithm, ai_model, request: gr.Request):
                success, message = preprocess(product_files, packaging_files, description_files, supplement, image_tiling_algorithm, ai_model, request)
                if not success:
                    return (
                        f"**识别未完成**：{message}",
                        gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update()
                    )
                if not redis_util.exists_key(request.session_hash):
                    return (
                        "**识别完成**，但未找到会话数据，请重试。",
                        gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update()
                    )
                redis_data = redis_util.get_value(request.session_hash)
                filled = _classification_to_precondition_values(redis_data.object_classify_response)
                if filled is None:
                    msg = "**识别完成**。未进行或未得到 AI 分类结果，请手动勾选前置条件。"
                    return (msg, gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update())
                msg = "**识别完成**。已根据 AI 分类结果预填下方前置条件，请核对后点击「保存并创建审核表单」。"
                return (msg,) + tuple(gr.update(value=v) for v in filled)

            start_btn.click(
                start_recognition,
                inputs=[product_file, packaging_file, description_file, supplement, image_tiling_algorithm, ai_model],
                outputs=[start_result_md, p1, p2, p3a, p3b, p3c, p3d, p4, p5]
            )

            def init_session_redis(request: gr.Request):
                print(f"init_session_redis: {request.session_hash}")
                return None
        with gr.Tab("审核结果"):
            gr.HTML("""
<div class="tutorial-box">
<h4>📖 审核结果页说明</h4>
<ul>
<li>请先在 <strong>「创建任务」</strong> 中上传材料并点击「保存并创建审核表单」，提交成功后再来本页。</li>
<li><strong>任务概览</strong>：查看当前任务摘要、勾选「条款筛选」可仅显示未通过项；勘误完成后点击「勘误完成, 生成数据」下载 Excel。</li>
<li><strong>审核条款列表</strong>：按章节逐条查看每条规则的证据图、AI 结论与人工勘误框。</li>
</ul>
</div>
""")
            with gr.Tabs() as result_inner_tabs:
                with gr.Tab("任务概览"):
                    gr.Markdown("### 任务详情")
                    task_details_md = gr.Markdown("", visible=False)
                    gr.Markdown("### 筛选与导出")
                    with gr.Row():
                        clause_filter_checkbox = gr.Checkbox(label="仅显示未通过条款", value=False, elem_id="clause_filter_checkbox")
                    with gr.Row():
                        generate_excel_btn = gr.Button("勘误完成, 生成数据", variant="primary", size="lg", visible=True)
                        download_excel_file = gr.File(label="下载 Excel 文件", interactive=False, visible=False)
                with gr.Tab("审核条款列表"):
                    gr.Markdown("### 按条款查看审核结果")
                    check_result_md = gr.Textbox("", visible=True, show_label=False)
                    gr.HTML("""
<style>
/* 处理所有gr-group相关元素，但排除表单控件 */
div.gr-group,
div.gr-group div:not(.form):not(.form *):not(label):not(input) {
    background: transparent !important;
    background-color: transparent !important;
    box-shadow: none !important;
    border: none !important;
    --background-fill-primary: transparent !important;
}
</style>
""")
                    review_outputs = []
                    acc_groups = []
                    manual_check_groups = []
                    for i in range(200):  # 最多200条规则
                        with gr.Group(visible=False) as acc_group:
                            acc_groups.append(acc_group)
                            with gr.Row():
                                chapter_title = gr.HTML(f"<h3>[待定]</h3>", visible=False)
                                review_outputs.append(chapter_title)
                            with gr.Row():
                                title_md = gr.HTML("<h3>标题 [待定]</h3>", visible=False)
                                review_outputs.append(title_md)
                                regulation_md = gr.HTML("<h3>[待定]</h3>", visible=False)
                                review_outputs.append(regulation_md)
                                with gr.Column():
                                    requirements_btn = gr.Button("详细要求", variant="primary", elem_classes=["rounded-button"], visible=True)
                                    review_outputs.append(requirements_btn)
                                    with gr.Group(visible=False, elem_id="modal-container") as modal:
                                        requirements_md = gr.Markdown("[待定]", visible=False)
                                        review_outputs.append(requirements_md)
                                    state = gr.State(False)
                                    def toggle_modal(show):
                                        return not show, gr.update(visible=not show)
                                    requirements_btn.click(fn=toggle_modal, inputs=state, outputs=[state, modal])
                                preconditions_md = gr.HTML("**[待定]**", visible=False)
                                review_outputs.append(preconditions_md)
                                exemption_clauses_md = gr.HTML("**[待定]**", visible=False)
                                review_outputs.append(exemption_clauses_md)
                            with gr.Row():
                                with gr.Column():
                                    description = gr.HTML(f"[待定]", visible=False)
                                    review_outputs.append(description)
                                    evidence_img = gr.HTML(visible=False)
                                    review_outputs.append(evidence_img)
                                with gr.Column():
                                    ai_conclusion = gr.HTML(f"[待定]", visible=False)
                                    ai_rule = gr.HTML("[待定]", visible=False)
                                    review_outputs.append(ai_conclusion)
                                    review_outputs.append(ai_rule)
                                with gr.Column():
                                    is_error = gr.Checkbox(label="错误", elem_id="is_error", visible=False, interactive=True)
                                    correct_conclusion = gr.Textbox(placeholder="请输入正确结论", lines=2, show_label=False, elem_id="correct_conclusion", visible=False)
                                    error_reason = gr.Textbox(placeholder="输入错误说明", lines=2, show_label=False, elem_id="error_reason", visible=False)
                                    review_outputs.append(is_error)
                                    review_outputs.append(correct_conclusion)
                                    review_outputs.append(error_reason)
                                    manual_check_groups.append(is_error)
                                    manual_check_groups.append(correct_conclusion)
                                    manual_check_groups.append(error_reason)
            def on_clause_filter_change(is_checked, request: gr.Request):
                redis_data = redis_util.get_value(request.session_hash)
                
                # 空值检查
                if redis_data is None:
                    error_msg = "redis_data 为空"
                    print(f"===================ERROR: {error_msg}")
                    return [error_msg] + [gr.update()]*(2800+200)
                
                rule_check_response = redis_data.rule_check_response
                
                # 空值检查
                if rule_check_response is None:
                    error_msg = "rule_check_response 为空"
                    print(f"===================ERROR: {error_msg}")
                    return [error_msg] + [gr.update()]*(2800+200)
                
                updates = []
                acc_updates = []
                #print(f"rule_check_response.get_check_results(): {rule_check_response.get_check_results()}")
                last_chapter = ""
                last_title = ""
                print(f"clause_filter_checkbox: {is_checked}")
                
                # 调试输出：检查 get_check_results 的长度
                check_results = rule_check_response.get_check_results()
                print(f"===================DEBUG: on_clause_filter_change, check_results length: {len(check_results)}")
                
                updates, acc_updates = list_task_review(rule_check_response, filter_pass_status=is_checked)
                return [*updates, *acc_updates]

            def show_task_details(product_files, packaging_files, description_files, supplement, image_tiling_algorithm, ai_model, age_from_input, age_from_unit, age_to_input, age_to_unit, request: gr.Request, *precondition_values):
                if redis_util.exists_key(request.session_hash):
                    redis_data = redis_util.get_value(request.session_hash)
                else:
                    return "未发现任务"
                # 生成任务详情的Markdown内容
                # precondition_values 是一个包含所有precondition_boxes值的元组
                md = f"""
| 项目             | 内容 |
|------------------|------|
| **任务ID**       | {request.session_hash} |
| **产品文件**     | {', '.join([os.path.basename(product_file.name) for product_file in product_files]) if product_files else '未上传'} |
| **包装文件**     | {', '.join([os.path.basename(packaging_file.name) for packaging_file in packaging_files]) if packaging_files else '未上传'} |
| **说明书**       | {', '.join([os.path.basename(description_file.name) for description_file in description_files]) if description_files else '未上传'} |
| **补充说明**     | {supplement} |
| **是否使用分图算法** | {image_tiling_algorithm} |
| **AI模型**       | {ai_model} |
| **前置条件**     | {', '.join([item for sublist in precondition_values for item in sublist]) if any(precondition_values) else '未选择'} |
| **设计年龄**     | {age_from_input} {age_from_unit} 到 {age_to_input} {age_to_unit} |
"""
                return gr.update(value=md, visible=True)

            submit_btn.click(
                show_task_details,
                inputs=[
                    product_file, packaging_file, description_file, supplement, image_tiling_algorithm, ai_model, age_from_input, age_from_unit,
                    age_to_input, age_to_unit, *precondition_boxes
                ],
                outputs=[task_details_md]
            )

            def generate_excel(request: gr.Request, *manual_check_groups):
                excel_generator = ExcelGenerator()
                try:
                    if redis_util.exists_key(request.session_hash):
                        redis_data = redis_util.get_value(request.session_hash)
                        if redis_data.rule_check_response is None:
                            msg = "当前任务没有可用的规则检查结果，可能是上游模型调用失败，请先重新运行审核。"
                            logging.error(msg)
                            print(msg)
                            return None
                        # 使用Excel文件名生成器
                        excel_name = excel_name_generator.generate_excel_name(request.session_hash)
                        excel_path = excel_generator.generate_review_excel(redis_data.rule_check_response, manual_check_groups,output_path = os.path.join("./work_dir/",request.session_hash,f"{excel_name}"))
                    else:
                        print(f"redis_data not exists")
                        return None
                    return excel_path
                except Exception as e:
                    print(f"生成Excel文件时出错: {e}")
                    return None
            generate_excel_btn.click(
                generate_excel,
                inputs=manual_check_groups,
                outputs=[download_excel_file]
            )

        def load_history_table(request: gr.Request):
            try:
                db_rows = db_client.list_audit_task_history(limit=200)
            except Exception as e:
                logging.error("查询审核历史失败: %s", e)
                return "查询历史失败，请检查数据库连接。"
            if not db_rows:
                return "暂无历史记录。"
            cols = ["任务ID", "产品文件", "包装文件", "说明书", "补充说明", "是否使用分图算法", "AI模型", "前置条件", "设计年龄", "创建时间"]
            rows = []
            for r in db_rows:
                created_at = r.get("created_at")
                if hasattr(created_at, "strftime"):
                    created_at = created_at.strftime("%Y-%m-%d %H:%M")
                elif created_at is not None:
                    created_at = str(created_at)[:16]
                else:
                    created_at = "-"
                rows.append({
                    "任务ID": r.get("session_hash") or "-",
                    "产品文件": r.get("product_filenames") or "-",
                    "包装文件": r.get("packaging_filenames") or "-",
                    "说明书": r.get("description_filenames") or "-",
                    "补充说明": (r.get("supplement") or "") or "-",
                    "是否使用分图算法": r.get("image_tiling_algorithm") or "-",
                    "AI模型": r.get("ai_model") or "-",
                    "前置条件": r.get("preconditions_str") or "-",
                    "设计年龄": r.get("age_str") or "-",
                    "创建时间": created_at,
                })
            header = "| " + " | ".join(cols) + " |"
            sep = "|" + "|".join(["---"] * len(cols)) + "|"
            def _cell(v, max_len=24):
                s = (v or "-").replace("|", " ").replace("\n", " ")
                return s[:max_len] + ("…" if len(s) > max_len else "")
            body_lines = []
            for row in rows:
                body_lines.append("| " + " | ".join(_cell(row.get(c, "-")) for c in cols) + " |")
            return header + "\n" + sep + "\n" + "\n".join(body_lines)

        with gr.Tab("历史") as history_tab:
            gr.HTML("""
<div class="tutorial-box">
<h4>📖 历史审核说明</h4>
<ul>
<li>本页从<strong>数据库</strong>查询过去的审核任务概览，便于追溯。</li>
<li>点击「查询历史」可刷新下方表格；进入本 Tab 时也会自动加载。</li>
</ul>
</div>
""")
            history_refresh_btn = gr.Button("查询历史", variant="secondary")
            history_table_md = gr.Markdown("暂无历史记录，请点击「查询历史」加载。", elem_classes=["usage-instruction"])
            history_refresh_btn.click(
                fn=load_history_table,
                inputs=[],
                outputs=[history_table_md]
            )
            history_tab.select(
                fn=load_history_table,
                inputs=[],
                outputs=[history_table_md]
            )

    def go_to_result_tab(product_files, packaging_files, description_files, supplement, image_tiling_algorithm, ai_model, age_from_input, age_from_unit, age_to_input, age_to_unit, request: gr.Request, *precondition_values):
        def _file_display(f):
            if f is None:
                return ""
            if hasattr(f, "name"):
                return os.path.basename(f.name)
            if isinstance(f, str):
                return os.path.basename(f)
            return str(f)

        if not redis_util.exists_key(request.session_hash):
            redis_data = RedisData()
            redis_util.set_value(request.session_hash, redis_data)
        redis_data = redis_util.get_value(request.session_hash)
        product_filenames = ", ".join([_file_display(p) for p in (product_files or [])]) or "未上传"
        packaging_filenames = ", ".join([_file_display(p) for p in (packaging_files or [])]) or "未上传"
        description_filenames = ", ".join([_file_display(p) for p in (description_files or [])]) or "未上传"
        supplement_str = supplement if supplement else ""
        preconditions_str = ", ".join([str(item) for sublist in (precondition_values or []) for item in (sublist if isinstance(sublist, list) else [sublist])]) if precondition_values else "未选择"
        age_str = f"{age_from_input or ''} {age_from_unit or ''} 到 {age_to_input or ''} {age_to_unit or ''}".strip() or "未填"
        redis_data.task_overview = {
            "product_filenames": product_filenames,
            "packaging_filenames": packaging_filenames,
            "description_filenames": description_filenames,
            "supplement": supplement_str,
            "image_tiling_algorithm": image_tiling_algorithm,
            "ai_model": ai_model,
            "preconditions_str": preconditions_str,
            "age_str": age_str,
        }
        if len(redis_data.rule_file_path) == 0:
            redis_data.rule_file_path = DEFAULT_EXCEL_PATH
        redis_util.set_value(request.session_hash, redis_data)
        try:
            db_client.upsert_audit_task_history(
                session_hash=request.session_hash,
                product_filenames=product_filenames,
                packaging_filenames=packaging_filenames,
                description_filenames=description_filenames,
                supplement=supplement_str,
                image_tiling_algorithm=image_tiling_algorithm,
                ai_model=ai_model,
                preconditions_str=preconditions_str,
                age_str=age_str,
            )
        except Exception as e:
            logging.error("写入审核历史表失败: %s", e)
        if len(redis_data.rule_file_path) == 0:
            return gr.update(value="✅ 提交成功，使用默认规则，请点击上方'审核结果'Tab查看结果！", visible=True)
        return gr.update(value="✅ 提交成功，请点击上方'审核结果'Tab查看结果！", visible=True)

    submit_btn.click(
        go_to_result_tab,
        inputs=[
            product_file, packaging_file, description_file, supplement, image_tiling_algorithm, ai_model,
            age_from_input, age_from_unit, age_to_input, age_to_unit, *precondition_boxes
        ],
        outputs=[submit_result]
    )

    def show_task_review(product_files, packaging_files, description_files, supplement, image_tiling_algorithm, ai_model, age_from_input, age_from_unit, age_to_input, age_to_unit, clause_filter_checkbox,request: gr.Request, *precondition_values):
        if True:
            success, message = preprocess(product_files, packaging_files, description_files, supplement, image_tiling_algorithm, ai_model, request)
            if not success:
                return [message] + [gr.update()]*(2800+200+3)
        if True:
            # precondition_values 是一个包含所有precondition_boxes值的元组
            print(f"show_task_review: {request.session_hash}")

            print(f"precondition_values: {precondition_values}")
            print(f"age_from: {age_from_input}")
            print(f"age_to: {age_to_input}")
            
            if redis_util.exists_key(request.session_hash):
                redis_data = redis_util.get_value(request.session_hash)
                # 将所有precondition_values合并为一个列表
                all_preconditions = [subitem for item in precondition_values for subitem in item]
                age_range_precondition = ""
                if age_from_input != "" or age_to_input != "":
                    if age_from_input == "" and age_to_input != "":
                        age_range_precondition = f"年龄:{age_to_input}{age_to_unit}及以下"
                    elif age_from_input != "" and age_to_input == "":
                        age_range_precondition = f"年龄:{age_from_input}{age_from_unit}及以上"
                    else:
                        age_range_precondition = f"年龄:{age_from_input}{age_from_unit}到{age_to_input}{age_to_unit}"
                    # all_preconditions.append(age_range_precondition)
                logging.info(f"all_preconditions: {all_preconditions}")
                logging.info(f"age_range_precondition: {age_range_precondition}")
                redis_data.manual_category_and_feature_data.toy_category = all_preconditions
                redis_data.manual_category_and_feature_data.features = all_preconditions
                redis_data.manual_category_and_feature_data.sub_features = all_preconditions
                redis_util.set_value(request.session_hash, redis_data)
            else:
                print(f"redis_data not exists")
                return ["redis_data not exists"] + [gr.update()]*(2800+200+3)
            for i in range(5):
                redis_data = redis_util.get_value(request.session_hash)
                if len(redis_data.rule_file_path) > 0:
                    break
                print(f"search rule_file_path: {i}")
                import time
                time.sleep(1)
            print(f"show_task_review: {redis_data.rule_file_path}")
            if len(redis_data.rule_file_path) == 0:
                print(f"redis_data.rule_file_path is empty")
                return ["redis_data.rule_file_path is empty"] + [gr.update()]*(2800+200+3)
            enable_cut_images = image_tiling_algorithm == "是"
            rule_excel_file_path = redis_data.rule_file_path
        
        if True:
            rules, annotated_results = read_rules(rule_excel_file_path, enable_human_annotated=True, select_rule_ids=None)
            
            # 调试输出：检查规则数量
            print(f"DEBUG: read_rules returned {len(rules)} rules")
            print(f"DEBUG: rule_excel_file_path: {rule_excel_file_path}")
            logging.info(f"read_rules returned {len(rules)} rules from {rule_excel_file_path}")
            
            # 空列表检查
            if len(rules) == 0:
                error_msg = f"规则列表为空！请检查规则文件: {rule_excel_file_path}"
                print(f"ERROR: {error_msg}")
                logging.error(error_msg)
                return [error_msg] + [gr.update()]*(2800+200+3)
            
            my_rule_check_config = model_config["rule_check_configs"]
            for key, value in object_classify_gpt_config[ai_model].items():
                my_rule_check_config[key] = value
            
            # 调试输出：打印配置信息
            print(f"DEBUG: my_rule_check_config keys: {list(my_rule_check_config.keys())}")
            logging.info(f"my_rule_check_config: {my_rule_check_config}")
            
            rule_check_agent = RuleCheckAgent(my_rule_check_config)
            print(f"DEBUG: rule_check_agent created successfully")
            cutted_product_images = {}
            cutted_package_images = {}
            cutted_manual_images = {}
            if enable_cut_images:
                if redis_data.image_cut_response is not None:
                    cutted_product_images = redis_data.image_cut_response.get_cutted_product_images()
                    cutted_package_images = redis_data.image_cut_response.get_cutted_package_images()
                    cutted_manual_images = redis_data.image_cut_response.get_cutted_manual_images()
                else:
                    print(f"WARNING: enable_cut_images=True but image_cut_response is None, using empty dicts")
                    logging.warning("enable_cut_images=True but image_cut_response is None")
            
            rule_check_request = RuleCheckRequest(task_id=request.session_hash,
                enable_cutted_images=image_tiling_algorithm == "是",
                product_images=redis_data.preprocessed_data[ImageType.PRODUCT] if ImageType.PRODUCT in redis_data.preprocessed_data else [], 
                package_images=redis_data.preprocessed_data[ImageType.PACKAGE] if ImageType.PACKAGE in redis_data.preprocessed_data else [], 
                manual_images=redis_data.preprocessed_data[ImageType.MANUAL] if ImageType.MANUAL in redis_data.preprocessed_data else [],
                cutted_product_images=cutted_product_images,
                cutted_package_images=cutted_package_images,
                cutted_manual_images=cutted_manual_images,
                toy_category=all_preconditions,
                product_features=[],
                sub_features=[],
                design_age_range=age_range_precondition,
                other_info=redis_data.user_input_data["other_info"]
                )

            # 调试输出：打印 rule_check_request 信息
            print(f"DEBUG: rule_check_request created")
            print(f"DEBUG: product_images count: {len(rule_check_request.get_product_images())}")
            print("fDEBUG: package_images count: {len(rule_check_request.get_package_images())}")
            print(f"DEBUG: manual_images count: {len(rule_check_request.get_manual_images())}")
            print(f"DEBUG: toy_category: {rule_check_request.get_toy_category()}")
            print(f"DEBUG: design_age_range: {rule_check_request.get_design_age_range()}")

            for rule in rules:
                rule_check_request.add_rule(rule)
            
            # 调试输出：打印添加规则后的数量
            print(f"DEBUG: Added {len(rules)} rules to rule_check_request")
            print(f"DEBUG: rule_check_request.get_rules() count: {len(rule_check_request.get_rules())}")
            
            rule_check_response = rule_check_agent.check_rules(rule_check_request)
            
            # 调试输出：规则检查前后的对比
            print(f"DEBUG: After check_rules, input rules: {len(rules)}, response check_results: {len(rule_check_response.get_check_results())}")
            task_id = rule_check_response.get_task_id()
            logging.info(f"rule_check_response: task_id={task_id}")
            
            # 调试输出：检查 rule_check_response
            print(f"DEBUG: rule_check_response is None: {rule_check_response is None}")
            if rule_check_response is not None:
                check_results = rule_check_response.get_check_results()
                print(f"DEBUG: rule_check_response.get_check_results() length: {len(check_results)}")
                print(f"DEBUG: rule_check_response.get_run_status(): {rule_check_response.get_run_status()}")
                print(f"DEBUG: rule_check_response.get_message(): {rule_check_response.get_message()}")
            else:
                print(f"ERROR: rule_check_response is None!")

            # ====== 将任务及本次检查结果写入数据库 ======
            try:
                if getattr(redis_data, "db_task_id", None) is None:
                    task_status = "finished" if rule_check_response and rule_check_response.get_run_status() else "failed"
                    preprocess_snapshot = redis_data.preprocessed_data if redis_data.preprocessed_data is not None else {}
                    db_task_id = db_client.create_task(
                        rule_file_path=rule_excel_file_path,
                        preprocess_data=preprocess_snapshot,
                        status=task_status,
                    )
                    redis_data.db_task_id = db_task_id
                else:
                    db_task_id = redis_data.db_task_id

                # 2. 写入对象分类结果
                if redis_data.object_classify_response is not None:
                    ocr = redis_data.object_classify_response
                    try:
                        db_client.create_object_classification_response(
                            task_id=db_task_id,
                            status="success" if ocr.get_status() else "failed",
                            message=ocr.get_message(),
                            reason=ocr.get_reason(),
                            category=",".join(list(ocr.get_toy_category() or [])) if hasattr(ocr, "get_toy_category") else None,
                            features={
                                "toy_category": list(ocr.get_toy_category() or []),
                                "product_features": list(ocr.get_product_features() or []),
                                "sub_features": list(ocr.get_sub_features() or []),
                            },
                        )
                    except Exception as e:
                        logging.error("write object_classification_response to DB failed: %s", e)

                # 2b. 加工后的 AI 分类与特性（与界面预填一致）
                try:
                    if getattr(redis_data, "ai_category_and_feature_data", None) is not None:
                        db_client.upsert_task_ai_category_feature(
                            db_task_id, redis_data.ai_category_and_feature_data
                        )
                except Exception as e:
                    logging.error("write task_ai_category_feature to DB failed: %s", e)

                # 3. 写入 rule_check_response 头记录
                if rule_check_response is not None:
                    db_rule_check_response_id = db_client.create_rule_check_response(
                        task_id=db_task_id,
                        run_status=rule_check_response.get_run_status(),
                        message=rule_check_response.get_message(),
                    )
                    redis_data.db_rule_check_response_id = db_rule_check_response_id

                    # 4. 写入每条规则的检查结果
                    for item in rule_check_response.get_check_results():
                        rule = item["rule"]
                        check_result = item["check_result"]
                        try:
                            db_rule_id = db_client.upsert_rule_and_get_id(rule)
                            db_client.create_rule_check_result(
                                rule_check_response_id=db_rule_check_response_id,
                                rule_id=db_rule_id,
                                check_result=check_result,
                            )
                        except Exception as e:
                            logging.error("write rule_check_result to DB failed: %s", e)

                # 刷新 redis_data 到存储
                redis_util.set_value(request.session_hash, redis_data)
            except Exception as e:
                logging.error("write task / rule_check data to DB failed: %s", e)

        # ...你的表单处理...
        if False:
            import time
            time.sleep(3)
            rule_check_response = RuleCheckResponse(status=True, message="success",task_id=request.session_hash)
            rule_check_result1 = RuleCheckResult()
            rule_check_result1.fill(run_status=True,
                                    message="success",
                                    necessity_state=False,
                                    necessity_reason="",
                                    pics=['apps/pic_sample.png']*5, 
                                    pass_status=True,
                                    # content
                                    llm_response="包装上有制造商名称。",
                                    # reason
                                    reason="因为包装上有制造商名称。")
            rule_id = 1
            rule_check_response.add_check_result(
                Rule(chapter="章节 01 General Labeling requirements", title="标题 One Time Use Products Fair Packaging and Labeling Act or All Other Products.  Uniform Packaging and Labeling Regulations", method="F.P. & L. Act (16 CFR 500) OR NIST Uniform Laws and Regulations  Handbook 130", requirements="1.这是真实要求1\n2.这是真实要求2\n3.这是真实要求3", audit_content="包装上有制造商、分销商、品牌名称三个中的任意一个，不检查名称真实性，只需要有即可。", llm_prompt="if 识别，remark识别的净含量， 提醒需要审核真实净含量。If 只标识了个数，没有精确净含量，或者没有标识个数和精确净含量，then Fail",group_id=None,rule_id=None,preconditions="前置条件",exemption_clauses="排他"), 
                rule_check_result1,
                rule_id)
            rule_check_result2 = RuleCheckResult()
            rule_check_result2.fill(run_status=True,
                                    message="success",
                                    necessity_state=True,
                                    necessity_reason="",
                                    pics=['apps/pic_sample.png']*5, 
                                    pass_status=True,
                                    # content
                                    llm_response="包装上有制造商名称。",
                                    # reason
                                    reason="因为包装上有制造商名称。")
            rule_id = 2
            rule_check_response.add_check_result(
                Rule(chapter="章节 01 General Labeling requirements", title="标题 One Time Use Products Fair Packaging and Labeling Act or All Other Products.  Uniform Packaging and Labeling Regulations", method="F.P. & L. Act (16 CFR 500) OR NIST Uniform Laws and Regulations  Handbook 130", requirements="1.这是真实要求1\n2.这是真实要求2\n3.这是真实要求3", audit_content="包装上有制造商、分销商、品牌名称三个中的任意一个，不检查名称真实性，只需要有即可。", llm_prompt="if 识别，remark识别的净含量， 提醒需要审核真实净含量。If 只标识了个数，没有精确净含量，或者没有标识个数和精确净含量，then Fail",group_id=None,rule_id=None,preconditions=None,exemption_clauses=None), 
                rule_check_result2,
                rule_id)
        
        # 空值检查
        if rule_check_response is None:
            error_msg = "规则检查响应为空，无法显示审核结果"
            print(f"===================ERROR: {error_msg}")
            logging.error(error_msg)
            return [error_msg] + [gr.update()]*(2800+200+3)
        
        # 即使 run_status=False，只要有检查结果就继续处理
        check_results = rule_check_response.get_check_results()
        if len(check_results) == 0:
            error_msg = "规则检查未返回任何结果"
            if not rule_check_response.get_run_status():
                error_msg = f"{error_msg}，错误信息: {rule_check_response.get_message()}"
            print(f"===================ERROR: {error_msg}")
            logging.error(error_msg)
            return [error_msg] + [gr.update()]*(2800+200+3)
        elif not rule_check_response.get_run_status():
            warning_msg = f"规则检查过程中出现错误: {rule_check_response.get_message()}，但仍有 {len(check_results)} 个结果可以显示"
            print(f"===================WARNING: {warning_msg}")
            logging.warning(warning_msg)
        
        redis_data.rule_check_response = rule_check_response
        set_success = redis_util.set_value(request.session_hash, redis_data)
        
        # 验证数据是否正确保存
        if set_success:
            verify_data = redis_util.get_value(request.session_hash)
            if verify_data is None or verify_data.rule_check_response is None:
                print(f"===================ERROR: 数据保存后验证失败")
                logging.error("数据保存后验证失败")
            else:
                print(f"===================DEBUG: 数据保存验证成功")
        else:
            print(f"===================ERROR: set_value 返回 False")
            logging.error("set_value 返回 False")
        
        updates = []
        acc_updates = []
        #print(f"rule_check_response.get_check_results(): {rule_check_response.get_check_results()}")
        last_chapter = ""
        last_title = ""
        print(f"clause_filter_checkbox: {clause_filter_checkbox}")
        
        # 调试输出：检查 get_check_results 的长度
        check_results = rule_check_response.get_check_results()
        print(f"===================DEBUG: Before list_task_review, check_results length: {len(check_results)}")
        
        updates, acc_updates = list_task_review(rule_check_response, filter_pass_status=clause_filter_checkbox)
        
        # 调试输出：检查 updates 和 acc_updates 的数量
        print(f"===================DEBUG: updates length: {len(updates)}, acc_updates length: {len(acc_updates)}")
        
        return [*updates, *acc_updates,gr.update(visible=False),gr.update(visible=True),gr.update(visible=True)]
    
    def list_task_review(rule_check_response: RuleCheckResponse, filter_pass_status: bool = False):
        # 调试输出：检查 rule_check_response
        print(f"===================DEBUG: list_task_review, rule_check_response is None: {rule_check_response is None}")
        
        if rule_check_response is None:
            print(f"===================ERROR: rule_check_response is None in list_task_review")
            return [gr.update(visible=False)] * 2800, [gr.update(visible=False)] * 200
        
        check_results = rule_check_response.get_check_results()
        print(f"===================DEBUG: list_task_review, get_check_results() returned: {check_results}")
        print(f"===================DEBUG: list_task_review, check_results length: {len(check_results)}")
        
        # 空列表检查
        if len(check_results) == 0:
            print(f"===================WARNING: check_results is empty!")
            logging.warning("check_results is empty in list_task_review")
        
        acc_updates = []
        updates = []
        last_chapter = ""
        last_title = ""
        not_pass_num = 0
        for i, check_result in enumerate(check_results):
            print(f"check_result['check_result'].necessity_state: {check_result['check_result'].necessity_state}")
            if filter_pass_status and check_result['check_result'].necessity_state == False:
                print(f"filter_pass_status: {filter_pass_status}")
                not_pass_num += 1
                continue
            acc_updates.append(gr.update(visible=True))
            # acc_updates.append(gr.update(visible=True))  # acc_chapter
            if last_chapter != check_result['rule'].chapter:
                updates.append(gr.update(visible=True, value=f"<h3>{check_result['rule'].chapter}</h3><hr>"))  # acc_chapter
                last_chapter = check_result['rule'].chapter
            else:
                updates.append(gr.update(visible=False))  # acc_chapter
            if last_title != check_result['rule'].title:
                updates.append(gr.update(value=f"<h3>{check_result['rule'].title}</h3><hr>", visible=True))  # title_md
                last_title = check_result['rule'].title
                updates.append(gr.update(value=f"<h3>{check_result['rule'].method}</h3><hr>", visible=True))  # regulation_md
                updates.append(gr.update(visible=True))  # requirements_btn
                updates.append(gr.update(value=f"{check_result['rule'].requirements}", visible=True))  # requirements_md
            else:
                # acc_updates.append(gr.update(visible=False))
                updates.append(gr.update(visible=False))  # title_md
                updates.append(gr.update(visible=False))  # regulation_md
                updates.append(gr.update(visible=False))  # requirements_btn
                updates.append(gr.update(visible=False))  # requirements_md
            updates.append(gr.update(value=f"{check_result['rule'].preconditions}", visible=False))  # preconditions_md
            updates.append(gr.update(value=f"{check_result['rule'].exemption_clauses}", visible=False))  # exemption_clauses_md
            updates.append(gr.update(value=f"{check_result['rule'].audit_content}", visible=True))  # description
            image_segment_html_generator = ImageSegmentHtmlGenerator()
            updates.append(gr.update(value=image_segment_html_generator.generate_html(check_result['check_result'].pics), visible=True))  # evidence_img
            display_result = "NA"
            if check_result['check_result'].pass_status is None:
                display_result = "NA"
            elif check_result['check_result'].pass_status:
                display_result = "Pass"
            else:
                display_result = "Fail"

            updates.append(gr.update(value=f"<strong>{display_result}，{check_result['check_result'].llm_response}，{check_result['check_result'].reason}</strong>" if check_result['check_result'].necessity_state else f"<strong>NA，{check_result['rule'].exemption_clauses}</strong>", visible=True))  # ai_conclusion
            updates.append(gr.update(value=f"{check_result['rule'].llm_prompt}", visible=True))  # ai_rule
            updates.append(gr.update(visible=True))  # is_error
            updates.append(gr.update(visible=True))  # correct_conclusion
            updates.append(gr.update(visible=True))  # error_reason

        for i in range(len(rule_check_response.get_check_results()) - not_pass_num, 200):
            acc_updates.append(gr.update(visible=False))  # acc_chapter
            updates.append(gr.update(value=None, visible=False))  # acc_chapter
            updates.append(gr.update(value=None, visible=False))  # title_md
            updates.append(gr.update(value=None, visible=False))  # regulation_md
            updates.append(gr.update(visible=False))  # requirements_btn
            updates.append(gr.update(value=None, visible=False))  # requirements_md
            updates.append(gr.update(value=None, visible=False))  # preconditions_md
            updates.append(gr.update(value=None, visible=False))  # exemption_clauses_md
            updates.append(gr.update(value=None, visible=False))  # description
            updates.append(gr.update(value=None, visible=False))  # evidence_img
            updates.append(gr.update(value=None, visible=False))  # ai_conclusion
            updates.append(gr.update(value=None, visible=False))  # ai_rule
            updates.append(gr.update(visible=False))  # is_error
            updates.append(gr.update(visible=False))  # correct_conclusion
            updates.append(gr.update(visible=False))  # error_reason
        
        # 验证输出数量
        expected_updates = 2800  # 200 * 14
        expected_acc_updates = 200
        print(f"updates: {len(updates)}, expected: {expected_updates}")
        print(f"acc_updates: {len(acc_updates)}, expected: {expected_acc_updates}")
        if len(updates) != expected_updates:
            print(f"ERROR: updates 数量不匹配! 实际: {len(updates)}, 期望: {expected_updates}")
            logging.error(f"updates 数量不匹配! 实际: {len(updates)}, 期望: {expected_updates}")
        if len(acc_updates) != expected_acc_updates:
            print(f"ERROR: acc_updates 数量不匹配! 实际: {len(acc_updates)}, 期望: {expected_acc_updates}")
            logging.error(f"acc_updates 数量不匹配! 实际: {len(acc_updates)}, 期望: {expected_acc_updates}")
        return updates, acc_updates

    submit_btn.click(
        show_task_review,
        inputs=[
            product_file, packaging_file, description_file, supplement,image_tiling_algorithm, ai_model, age_from_input, age_from_unit, age_to_input, age_to_unit, clause_filter_checkbox, *precondition_boxes
        ],
        outputs=[*review_outputs, *acc_groups,check_result_md,generate_excel_btn,download_excel_file]
    )

    clause_filter_checkbox.change(
        fn=on_clause_filter_change,
        inputs=[clause_filter_checkbox],
        outputs=[*review_outputs, *acc_groups]
    )

app = gr.mount_gradio_app(app, demo, path="/")
uvicorn.run(app, host='', port=)




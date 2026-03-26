from agents.image_cut.image_cut_request import ImageCutRequest
from agents.image_cut.image_cut_response import ImageCutResponse
from agents.agent_utils import ImageType
from agents.image_cut.models.sam_model import SamModel
from agents.image_cut.models.fastsam_model import FastSAMModel
from agents.image_cut.models.ocr_model import OcrModel
from agents.image_cut.models.dotted_line_detector import DottedLineDetector
from agents.image_cut.models.vlm_cut_model import VlmCutModel
from agents.image_cut.models.post_processor import PostProcesser
import logging
from PIL import Image
from glob import glob
import numpy as np
import cv2
import time
import traceback
import os
from agents.agent_utils import CutType
import time

class ImageCutModel:
    '''
    切图模型
    '''
    def __init__(self, model_configs: dict):
        self._model_configs = model_configs
        self._enable_vlm_cut = model_configs["enable_vlm_cut"] if "enable_vlm_cut" in model_configs else True   
        self._enable_ocr_cut = model_configs["enable_ocr_cut"] if "enable_ocr_cut" in model_configs else True
        self._enable_sam_cut = model_configs["enable_sam_cut"] if "enable_sam_cut" in model_configs else True

        self._enable_package_cut = True
        self._enable_manual_cut = False
        self._enable_product_cut = False
        
        # 切图的最小尺寸，如果图片尺寸小于这个值，则不切图
        self._cut_min_size = model_configs["cut_min_size"] if "cut_min_size" in model_configs else 1024

        self._dotted_line_detector = DottedLineDetector()
        self._same_model_name = model_configs["sam_model_name"]
        self._sam_max_size = model_configs["sam_max_size"]
        self._sam_device_id = model_configs["sam_device_id"]
        self._sam_conf = model_configs["sam_conf"]
        self._sam_iou = model_configs["sam_iou"]
        self._ocr_sam_iou_threshold = model_configs["ocr_sam_iou_threshold"]
        self._debug = model_configs["debug"] if "debug" in model_configs else False
        # 是否 debug 模式，debug 模式会保存过程图片和 log
        self._model_input_size = model_configs["model_input_image_size"]
        # 下游模型要求的输入大小，例如（768,768）
        self._cut_mode = model_configs["cut_mode"]
        # 切图模式：PER_BOUNDING_BOX（逐框保存）或 STACK_BOUNDING_BOX（多框堆叠拼接成几张图）
        
        
        self._sam_model = None# 初始化 SAM 模型（根据配置选择 FastSAM 或原版 SAM）
        if self._enable_sam_cut:
            if self._same_model_name == "FastSAM":
                device_id = "cpu" if self._sam_device_id is None else self._sam_device_id
                self._sam_model = FastSAMModel(model_path=model_configs["sam_model_ckpt"])
            else:
                self._sam_model = SamModel(model_configs["sam_model_name"], model_configs["sam_model_ckpt"], model_configs["sam_device_id"])

        self._ocr_model = None# 初始化 OCR 模型
        if self._enable_ocr_cut:
            self._ocr_model = OcrModel()
        self._vlm_cut_model = None# 初始化大模型 VLM 切图模块
        if self._enable_vlm_cut:
            self._vlm_cut_model = VlmCutModel(model_configs["vlm_cut_model_configs"])
        # 初始化后处理器：负责融合 SAM/OCR/VLM 输出，输出最后的框
        self._post_processer = PostProcesser(model_configs["sam_occupy_ratio"], model_configs["ocr_sam_iou_threshold"], model_configs["model_input_image_size"], self._debug)
        # 过滤占比过大的框  # OCR 与 SAM 框的 IoU 阈值  # 输入大小
        logging.info(f"initialized ImageCutModel with {model_configs}")



    def cut_images(self, request: ImageCutRequest) -> ImageCutResponse:
        logging.info(f"start to cut images with request: {request}")
        start_time = time.time()
        task_id = request.get_task_id()
        response = ImageCutResponse()
        # 如果debug模式，则创建debug目录
        product_debug_dir = None
        package_debug_dir = None
        manual_debug_dir = None
        if self._debug:
            product_debug_dir = os.path.join(request.get_work_dir(), task_id, ImageType.PRODUCT, "debug")
            os.makedirs(product_debug_dir, exist_ok=True)
            package_debug_dir = os.path.join(request.get_work_dir(), task_id, ImageType.PACKAGE, "debug")
            os.makedirs(package_debug_dir, exist_ok=True)
            manual_debug_dir = os.path.join(request.get_work_dir(), task_id, ImageType.MANUAL, "debug")
            os.makedirs(manual_debug_dir, exist_ok=True)
        # 处理产品图片(不切图)
        for product_image in request.get_product_images():
            logging.info(f"start to process to cut product image: {product_image}, task_id={task_id}")
            for my_product_image in glob(product_image):
                logging.info(f"start to process to cut my product image: {my_product_image}, task_id={task_id}")
                if self._enable_product_cut:
                    cutted_paths = self.cut_one_image(my_product_image, request.get_work_dir(), task_id, ImageType.PRODUCT, product_debug_dir)
                    response.add_cutted_product_image(my_product_image, cutted_paths)
                else:
                    response.add_cutted_product_image(my_product_image, [my_product_image])
            
        # 处理包装图片
        for package_image in request.get_package_images():
            logging.info(f"start to process to cut product image: {package_image}, task_id={task_id}")
            for my_package_image in glob(package_image):
                logging.info(f"start to process to cut my product image: {my_package_image}, task_id={task_id}")
                if self._enable_package_cut:
                    cutted_paths = self.cut_one_image(my_package_image, request.get_work_dir(), task_id, ImageType.PACKAGE, package_debug_dir)
                    response.add_cutted_package_image(my_package_image, cutted_paths)
                else:
                    response.add_cutted_package_image(my_package_image, [my_package_image])
            
        # 处理说明书图(不切图)
        for manual_image in request.get_manual_images():
            for my_manual_image in glob(manual_image):  
                if self._enable_manual_cut:
                    cutted_paths = self.cut_one_image(my_manual_image, request.get_work_dir(), task_id, ImageType.MANUAL, manual_debug_dir)
                    response.add_cutted_manual_image(my_manual_image, cutted_paths)
                else:
                    response.add_cutted_manual_image(my_manual_image, [my_manual_image])
        cost_time = time.time() - start_time
        logging.info(f"end to cut images with request: {request} finished, response: {response}, cost_time={cost_time}")

        return response

    '''
        切一张图, 并将结果按 work_dir/task_id/image_type/cutted/image_name 保存
    '''

    # 记录开始切单张图片的日志，包含路径、工作目录、任务 id、图片类型等信息
    def cut_one_image(self, original_image_path, work_dir, task_id, image_type, show_dir=None) -> list[str]:
        logging.info(f"start to cut one image: original_image_path={original_image_path}, work_dir={work_dir}, task_id={task_id}, image_type={image_type}")
        start_time = time.time()
        original_image_base = os.path.basename(original_image_path)
        if show_dir is not None:
            show_path = os.path.join(show_dir, original_image_base)
        else:
            show_path = None
        cutted_image_paths = [original_image_path]
        try:
            image = Image.open(original_image_path)
            # 将 PIL 图像转为 numpy 数组，方便 OpenCV 操作
            image = np.array(image)
            # 确保图像有3个通道
            if len(image.shape) == 2:  # 灰度图像
                image = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
            elif len(image.shape) == 3 and image.shape[2] == 1:  # 单通道图像
                image = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
            elif len(image.shape) == 3 and image.shape[2] == 4:  # RGBA图像
                image = cv2.cvtColor(image, cv2.COLOR_RGBA2BGR)
            else:
                image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
                # 常见 RGB -> BGR 转换（PIL 给出的是 RGB）

            height, width, _ = image.shape# 获取图像高度与宽度，并计算最大边
            max_size = max(height, width)
            if max_size < self._cut_min_size:# 若图像太小（小于设定最小切图阈值），则直接返回原始路径（不进行切图）
                return cutted_image_paths

            logging.info(f"image shape: {str(image.shape)}, original_image_path={original_image_path}, task_id={task_id}")
            # 打日志记录图像尺寸信息

            ############################ 1. 基于SAM的切图 ############################
            # 初始化 sam_masks 与 sam_contours（如果启用 SAM，会被覆盖）
            sam_masks, sam_contours = None, None
            if self._enable_sam_cut:
                if self._same_model_name == "FastSAM":
                    # FastSAM 支持直接以路径推理（其 infer 接口在 FastSAMModel 中实现）
                    sam_masks, sam_contours = self._sam_model.infer(original_image_path)
                else:
                    # 对于原版 SAM，先将图像缩放到设定的最大尺寸（避免 OOM），并获得缩放 ratio
                    resized_image, ratio = self.resize_image_to_maxsize(image, self._sam_max_size)
                    sam_masks, sam_contours = self._sam_model.infer(resized_image, ratio)
                    # 使用 SAM 模型的 infer（需要传入缩放后的图像及 ratio，以便恢复坐标）

            ############################ 2. 基于OCR的切图 ############################
            # 根据图片输入大小自适应选择分辨
            # 根据最大边尺寸动态选择 OCR 推理策略（直接 infer 或者切块 infer_tts）
            ocr_result = None
            if self._enable_ocr_cut:
                if max_size < 2024:# 小图直接推理
                    ocr_result = self._ocr_model.infer(image)
                elif max_size < 4032:# 中等图像使用 2x2 网格分块推理，减小内存峰值
                    ocr_result = self._ocr_model.infer_tts(image, grid_num=2)
                else:# 超大图像使用更细的 4x4 网格分块推理
                    ocr_result = self._ocr_model.infer_tts(image, grid_num=4)
                if ocr_result is None:
                    logging.error(f"{original_image_path} is all None")

            ############################ 3. 基于VLM的切图 ############################
            # VLM（视觉语言模型）通常通过大模型来判断图片中感兴趣的区域
            vlm_result = None
            if self._enable_vlm_cut:
                # VLM 模块对原始图片路径进行处理并返回区域信息
                vlm_result = self._vlm_cut_model.cut_image(original_image_path)

            # 一些中间变量（如检测表格的 box 或特殊轮廓）
            table_boxes = None
            target_contour = None
            # 如果需要，可以启用虚线检测器来检测分割区域（当前被注释）
            #target_contour = self._dotted_line_detector.infer(image, 1.0, page_tag=None)

            # 将 SAM / OCR / VLM 的结果传入后处理器，融合并得到最终的 bounding boxes（过滤、合并等）
            filtered_boundingboxes = self._post_processer.process(task_id, image, vlm_result, ocr_result, sam_masks, sam_contours, table_boxes, target_contour, show_path)
            # 根据设定的切图模式来执行不同的保存策略
            if self._cut_mode == CutType.PER_BOUNDING_BOX:# 每个 bounding box 单独保存为一张图片
                cutted_image_paths = self.cut_image_by_boundingboxes(image, original_image_path, filtered_boundingboxes, work_dir, task_id, image_type)
            elif self._cut_mode == CutType.STACK_BOUNDING_BOX:# 将多个小 bounding box 堆叠拼接到尽量少的几张图上保存
                cutted_image_paths = self.stack_image_by_boundingboxes(image, original_image_path, filtered_boundingboxes, work_dir, task_id, image_type)
        except Exception as e:
            traceback.print_exc()
            logging.error(f"error when cutting image: {original_image_path}, error: {e}")
        cost_time = time.time() - start_time
        # 计算单张图耗时并记录日志，包含裁剪后路径数量和列表
        logging.info(f"end to cut one image: cost_time={cost_time}sec, original_image_path={original_image_path}, task_id={task_id} finished, cutted_image_paths={len(cutted_image_paths)}, cutted_image_paths={cutted_image_paths}")
        return cutted_image_paths
    
    '''
        根据轮廓切图
    '''
    def cut_image_by_boundingboxes(self, image, image_path, filtered_boundingboxes, work_dir, task_id, image_type):
        cutted_image_paths = [] # 记录即将按框裁剪的数量
        logging.info(f"start to cut_image_by_boundingboxes! {len(filtered_boundingboxes)}")
        # 遍历每个过滤后的 bounding box，并裁剪保存
        for index, bbox in enumerate(filtered_boundingboxes):
            x, y, w, h = bbox
            cropped_image = image[y:y+h, x:x+w]
            # 获取原始图片的基础路径名
            base_name = os.path.splitext(os.path.basename(image_path))[0]
            # 创建保存目录
            save_dir = os.path.join(work_dir, task_id, image_type, "cutted")
            os.makedirs(save_dir, exist_ok=True)
            # 生成保存路径
            save_path = os.path.join(save_dir, f"{base_name}_{index}.jpg")
            # 保存裁剪后的图片
            cv2.imwrite(save_path, cropped_image)
            cutted_image_paths.append(save_path)
            #logging.info(f"Saved cropped image: {save_path}")
        return cutted_image_paths

    def stack_image_by_boundingboxes(self, image, image_path, filtered_boundingboxes, work_dir, task_id, image_type):
        cutted_image_paths = []
        logging.info(f"start to stack_image_by_boundingboxes! {len(filtered_boundingboxes)}, task_id={task_id}")
        # 获取模型输入尺寸
        target_height, target_width = self._model_input_size
        
        # 分别存储大图和小图
        large_images = []
        small_images = []

        # 将每个 box 对应的裁剪图分为大图或小图（判断依据为是否超过模型输入尺寸）
        for index, bbox in enumerate(filtered_boundingboxes):
            x, y, w, h = bbox
            cropped_image = image[y:y+h, x:x+w]
            
            # 检查图片尺寸是否超过模型输入大小
            # 如果宽或高超过目标宽高之一，视为大图需要单独保存
            if w > target_width or h > target_height:
                large_images.append((cropped_image, index))
            else:# 否则归为小图，准备堆叠
                small_images.append((cropped_image, index))
        
        gid = 0
        # 处理大图 - 单独保存
        for cropped_image, index in large_images:
            base_name = os.path.splitext(os.path.basename(image_path))[0]
            save_dir = os.path.join(work_dir, task_id, image_type, "cutted")
            os.makedirs(save_dir, exist_ok=True)
            save_path = os.path.join(save_dir, f"{base_name}_{gid}.jpg")
            gid += 1
            cv2.imwrite(save_path, cropped_image)
            cutted_image_paths.append(save_path)
        
        # 处理小图 - 独立处理
        # 处理小图 - 重新布局到尽量少的图片上
        if small_images:
            # 计算需要的画布数量
            total_area = sum(img.shape[0] * img.shape[1] for img, _ in small_images)
            canvas_area = target_height * target_width
            estimated_canvases = max(1, int(total_area / canvas_area * 1.5))  # 1.5倍缓冲
            
            # 创建画布列表
            canvases = []
            current_canvas = np.zeros((target_height, target_width, 3), dtype=np.uint8)
            current_canvas.fill(255)  # 白色背景
            canvas_occupied_areas = []  # 记录每个画布已占用的区域
            
            for cropped_image, index in small_images:
                img_h, img_w = cropped_image.shape[:2]
                
                # 寻找可以放置的位置
                placed = False
                for canvas_idx, (canvas, occupied_areas) in enumerate(zip(canvases, canvas_occupied_areas)):
                    # 检查是否可以在当前画布上放置
                    for y in range(0, target_height - img_h + 1, 10):  # 10像素步长
                        for x in range(0, target_width - img_w + 1, 10):
                            # 检查是否与已占用的区域重叠
                            overlap = False
                            for occupied_x, occupied_y, occupied_w, occupied_h in occupied_areas:
                                if (x < occupied_x + occupied_w and x + img_w > occupied_x and
                                    y < occupied_y + occupied_h and y + img_h > occupied_y):
                                    overlap = True
                                    break
                            
                            if not overlap:
                                # 放置图片
                                canvas[y:y+img_h, x:x+img_w] = cropped_image
                                occupied_areas.append((x, y, img_w, img_h))
                                placed = True
                                break
                        if placed:
                            break
                    if placed:
                        break
                
                # 如果无法在现有画布上放置，创建新画布
                if not placed:
                    new_canvas = np.zeros((target_height, target_width, 3), dtype=np.uint8)
                    new_canvas.fill(255)
                    new_canvas[0:img_h, 0:img_w] = cropped_image
                    canvases.append(new_canvas)
                    canvas_occupied_areas.append([(0, 0, img_w, img_h)])
            
            # 保存所有画布
            for canvas_idx, canvas in enumerate(canvases):
                base_name = os.path.splitext(os.path.basename(image_path))[0]
                save_dir = os.path.join(work_dir, task_id, image_type, "cutted")
                os.makedirs(save_dir, exist_ok=True)
                save_path = os.path.join(save_dir, f"{base_name}_stack_{gid}.jpg")
                gid += 1
                cv2.imwrite(save_path, canvas)
                cutted_image_paths.append(save_path)

        return cutted_image_paths

    # 将图像缩放到 max_size（若原始最大边超过 max_size），并返回缩放后的图像与缩放比例
    def resize_image_to_maxsize(self, image, max_size):
        height, width, _ = image.shape
        ori_max_size = max(height, width)
        # 如果原始最大边大于目标最大边，则进行缩放
        if ori_max_size > max_size:
            # 计算缩放比例（保持长宽比）
            resized_ratio = max_size / ori_max_size
            resized_height =  int(height * resized_ratio)
            resized_width = int(width * resized_ratio)
            resized_image = cv2.resize(image, (resized_width, resized_height))
            # 使用 OpenCV 的 resize 得到缩放后的图像
            return resized_image, resized_ratio# 返回缩放后的图像和缩放比例（用于恢复坐标）
        else:
            return image.copy(), 1# 若不需要缩放，返回图像的副本和比例 1


if __name__ == "__main__":
    import os
    # 配置日志
    os.makedirs("./logs", exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s',
        handlers=[
            logging.FileHandler("./logs/image_cut.log"),
            logging.StreamHandler()
        ],
        force=True
    )
    model_configs = {
        "enable_vlm_cut": True,
        "enable_ocr_cut": False,
        "enable_sam_cut": False,
        "sam_model_name": "FastSAM",
        "sam_model_ckpt": "./models/FastSAM-s.pt",
        "sam_device_id": "cpu",
        "sam_max_size": 512,
        "sam_conf": 0.15,
        "sam_iou": 0.5,
        "sam_occupy_ratio": 0.35, # 过滤超过这个占比的框
        "ocr_sam_iou_threshold": 0.1, # iou threshold
        "model_input_image_size": (768, 768), # 下游模型的图片输入大小(height, width)
        "cut_mode": CutType.STACK_BOUNDING_BOX,
        "vlm_cut_model_configs": {
            ?
        },
        "debug": True
    }
    cut_model = ImageCutModel(model_configs)
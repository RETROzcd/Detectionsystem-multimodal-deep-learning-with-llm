import logging
from pdf2image import convert_from_path
from glob import glob 
from agents.agent_utils import ImageType
import cv2
import shutil
import os
import numpy as np
import time
from PIL import Image
Image.MAX_IMAGE_PIXELS = 1000000000

class DataPreprocess:
    def __init__(self, model_configs: dict):
        """
        初始化DataPreprocess类
        
        Args:
            model_configs: 模型配置字典
        """
        self._model_configs = model_configs
        self._supported_filetype = model_configs["supported_filetype"]
        logging.info(f"DataPreprocess initialized with model_configs: {model_configs}")
    
    '''
        {
            task_id="123",
            product_images=["./samples/T52510260108TP-高拍仪/产品/*.jpg"],
            package_images=["./samples/T52510260108TP-高拍仪/包装/*.jpg"],
            manual_images=["./samples/T52510260108TP-高拍仪/说明书/*.jpg"],
             work_dir="/code/ys_dev/tmp"
        }
    '''
    def process(self, input_data: dict) -> dict:
        """
        处理图片数据 glob - > pdf->image
        """
        output_data = {}
        task_id = input_data["task_id"]
        output_data["task_id"] = task_id
        work_dir = input_data["work_dir"]
        output_data["work_dir"] = work_dir
        product_images = input_data["product_images"]
        package_images = input_data["package_images"]
        manual_images = input_data["manual_images"]
        # 保存处理后的图片到原始图片的映射
        processed2original_map = {}
        
        all_image_datas = []
        
        for image_patterns, image_type in [(product_images, ImageType.PRODUCT), (package_images, ImageType.PACKAGE), (manual_images, ImageType.MANUAL)]:
            if len(image_patterns) > 0:
                logging.info(f"Processing {image_type} images: {image_patterns}")
                for pattern in image_patterns:
                    for data_path in glob(pattern):
                        if any(data_path.endswith(filetype) for filetype in self._supported_filetype):
                            all_image_datas.append(data_path)
                            # Process each item
                            processed_paths = self.preprocess_one_item(data_path, work_dir, task_id, str(image_type))
                            if str(image_type) not in output_data:
                                output_data[str(image_type)] = []
                            output_data[str(image_type)].extend(processed_paths)
                            for processed_path in processed_paths:
                                processed2original_map[processed_path] = data_path
        
        output_data["processed2original_map"] = processed2original_map
        logging.info(f"data preprocessed: result={output_data}, task_id={task_id}")
        
        return output_data

    '''
        处理一个数据，如果是pdf转成多张图片，放到特定目录下 work_dir/task_id/image_type/original/..
    '''
    def preprocess_one_item(self, data_path: str, work_dir: str, task_id: str, image_type: str):
        image_paths = []
        save_dir = os.path.join(work_dir, task_id, image_type, "original")
        os.makedirs(save_dir, exist_ok=True)
        
        if data_path.endswith(".pdf"):
            # 处理pdf数据
            tag = os.path.basename(data_path).replace(".pdf", "")

            #images = convert_from_path(data_path)
            images = convert_from_path(
                data_path,
                poppler_path=r"D:\pyenvir\poppler-24.08.0\Library\bin"
            )
            for page_no, image in enumerate(images):
                target_path = os.path.join(save_dir, tag + "_page_" + str(page_no + 1) + ".jpg")
                image = np.array(image) # RGB
                if len(image.shape) == 3 and image.shape[2] == 3:  # 检查是否为3通道RGB图像
                    image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)  # RGB转BGR
                cv2.imwrite(target_path, image)
                image_paths.append(target_path)
        else:
            # 处理其他图片格式
            # 复制图片文件到目标目录
            filename = os.path.basename(data_path)
            target_path = os.path.join(save_dir, filename)
            # 读取图片文件
            image = cv2.imread(data_path)
            if image is None:
                logging.error(f"Failed to read image: {data_path}, task_id={task_id}")
            else:
                # 确保图片是BGR格式
                if len(image.shape) == 3:
                    if image.shape[2] == 3:
                        # 已经是BGR格式，直接保存
                        cv2.imwrite(target_path, image)
                    elif image.shape[2] == 4:
                        # RGBA格式，转换为BGR
                        image = cv2.cvtColor(image, cv2.COLOR_RGBA2BGR)
                        cv2.imwrite(target_path, image)
                    else:
                        # 其他3通道格式，转换为BGR
                        image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
                        cv2.imwrite(target_path, image)
                else:
                    # 如果是灰度图或其他格式，转换为BGR
                    image = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
                    cv2.imwrite(target_path, image)
                image_paths.append(target_path)
        
        return image_paths

if __name__ == "__main__":
    import os
    # 配置日志
    os.makedirs("./logs", exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s',
        handlers=[
            logging.FileHandler("./logs/data_preprocess.log"),
            logging.StreamHandler()
        ],
        force=True
    )

    model_config = {"supported_filetype": {"pdf", "jpg", "png", "jpeg"}}
    dp = DataPreprocess(model_config)
    input_data = {
        "task_id": "88-2",
        "product_images":[],
        "package_images":['./work_dir/ltrod2aq3o/package_images/H54809-04257 9ft Spellcaster Witch With Spellbook_IM.pdf'],
        "manual_images":['./work_dir/ltrod2aq3o/manual_images/H54809-04257-9ft Witch Spell Book.pdf'],
        "work_dir": "/code/ys_dev/tmp"
    }
    output_data = dp.process(input_data)
    print(output_data)


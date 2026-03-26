
from paddleocr import PaddleOCR, draw_ocr
import logging
import time
import numpy as np
import cv2
class OcrModel:

    def __init__(self) -> None:
        self.ocr = PaddleOCR(use_angle_cls=True, 
                            lang='en')

    def infer(self, image_data):
        logging.info(f"start to infer ocr model!")
        start_time = time.time()
        infer_result = []
        result = self.ocr.ocr(image_data,
                            cls=True)
        result = result[0]
        for idx in range(len(result)):
            res = result[idx]
            box = res[0]
            txt = res[1][0]
            score = res[1][1]
            infer_result.append({"box" : box, "txt": txt, "score": score})
        logging.info(f"end to infer ocr model! cost_time: {time.time() - start_time}, infer_result={len(infer_result)}")
        return infer_result
    
    '''
        box: list of points (x1, y1)
        boxes, local_region, (lh, lw), (height, width)
    '''
    def bbox2original(self, boxes, lregion, lhw, ghw):
        result = []
        for i, p in enumerate(boxes):
            px = lregion[0] + p[0] / lhw[1] * (lregion[2] - lregion[0])
            px = int(px * ghw[1])
            py = lregion[1] + p[1] / lhw[0] * (lregion[3] - lregion[1])
            py = int(py * ghw[0])
            result.append((px, py))
        return result
    
    def infer_tts(self, image_data, grid_num=8):
        start_time = time.time()
        # left, top, right, bottom    
        local_regions = []
        # level1
        #local_regions.append([0, 0, 1.0, 1.0])
        # level2
        #grid_num = 8 #4
        grid_x_size = 1 / grid_num * 1.2
        grid_y_size = 1 / grid_num * 1.2 
        xx = np.linspace(0 + 1 / grid_num * 0.5, 1 - 1 / grid_num * 0.5, num=grid_num)
        yy = np.linspace(0 + 1 / grid_num * 0.5, 1 - 1 / grid_num * 0.5, num=grid_num)
        xx, yy = np.meshgrid(xx, yy)
        for x, y in zip(xx.flatten(), yy.flatten()):
            left = max(x - grid_x_size * 0.5, 0)
            top = max(y - grid_x_size * 0.5, 0)
            right = min(x + grid_y_size * 0.5, 1.0)
            bottom = min(y + grid_y_size * 0.5, 1.0)
            if left < right and top < bottom:
                local_regions.append([left, top, right, bottom])

        height, width, _ = image_data.shape
        
        infer_result = []
        for local_region in local_regions:
            left = max(int(width * local_region[0]), 0)
            top = max(int(height * local_region[1]), 0)
            right = min(int(width * local_region[2]), width - 1)
            bottom = min(int(height * local_region[3]), height - 1)
            if left < right and top < bottom:
                local_image = image_data[top:bottom, left:right, :]
                lh, lw, _ = local_image.shape
                result = self.ocr.ocr(local_image, cls=True)
                if result is None:
                    continue
                result = result[0]
                if result is None:
                    continue
                for idx in range(len(result)):
                   res = result[idx]
                   boxes = res[0]
                   new_boxes = self.bbox2original(boxes, local_region, (lh, lw), (height, width))
                   txts = res[1][0]
                   scores = res[1][1]
                   infer_result.append({"box" : new_boxes, "txt": txts, "score": scores})
        
        cost_time = time.time() - start_time
        logging.info(f"ocr cost time: {cost_time}, grid_num={grid_num}")
        return infer_result
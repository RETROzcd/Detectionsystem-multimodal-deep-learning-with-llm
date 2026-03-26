import cv2
import numpy as np
from ultralytics.models.fastsam import FastSAM
import time
import logging


class FastSAMModel:

    def __init__(self, model_path="./models/FastSAM-s.pt", device="cpu", imgsz=256, conf=0.15, iou=0.5):
        self._model = FastSAM(model_path)
        self._device = "cpu"
        self._imgsz = imgsz
        self._conf = conf
        self._iou = iou
        logging.info(f"init FastSAMModel: device={self._device}, imgsz={self._imgsz}, conf={self._conf}, iou={self._iou}")

    def infer(self, image_path):
        logging.info(f"start to infer fastsam model!")
        start_time = time.time()
        results = self._model(image_path, device=self._device, retina_masks=True, imgsz=self._imgsz, conf=self._conf, iou=self._iou)
        result = results[0]  # Get the first result
        boxes = result.boxes  # Get the boxes for the first result
        masks = result.masks  # Get the masks for the first result
        conf = boxes.conf
        xywh = boxes.xywh
        contours = []
        for i, (box, confidence) in enumerate(zip(xywh, conf)):
            x, y, w, h = box.cpu().numpy()
            x1, y1 = int(x - w/2), int(y - h/2)
            x2, y2 = int(x + w/2), int(y + h/2)
            # 将bounding box的四个顶点构成contour
            contour = np.array([[x1, y1], [x2, y1], [x2, y2], [x1, y2]], dtype=np.int32)
            contours.append(contour)
        cost_time = time.time() - start_time
        logging.info(f"end to infer fastsam model!  cost time: {cost_time}, total_contours: {len(contours)}")
        return masks, contours

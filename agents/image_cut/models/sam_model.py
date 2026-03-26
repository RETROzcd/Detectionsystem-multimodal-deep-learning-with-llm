from segment_anything import SamAutomaticMaskGenerator, sam_model_registry
import logging
import torch
import time
import numpy as np
import cv2
from pycocotools import mask as mask_utils
import logging

class SamModel:

    def __init__(self, model_type, checkpoint, device_id=0) -> None:
        self._sam = sam_model_registry[model_type](checkpoint=checkpoint)
        if device_id is not None:
            torch.cuda.set_device(device_id)
            torch_device = torch.device(device_id)
            self._sam.to(device=torch_device)
        else:
            self._sam.to(device=torch.device("cpu"))
        logging.info(f"init sam model! model_type={model_type}, checkpoint={checkpoint}, device_id={device_id}")

    def infer(self, image_data, ratio):
        logging.info(f"start to infer sam model!")
        start_time = time.time()
        mask_generator = SamAutomaticMaskGenerator(self._sam)
        masks = mask_generator.generate(image_data)
        cost_time = time.time() - start_time
        contours = self.extract_polygons(masks, ratio)
        cost_time = time.time() - start_time
        logging.info(f"end to infer sam model!  cost time: {cost_time}, total_contours: {len(contours)}")
        return masks, contours
    
    def extract_polygons(self, anns, ratio):
        if len(anns) == 0:
            return
        sorted_anns = sorted(anns, key=(lambda x: x['area']), reverse=True)
        all_contours = []
        #all_occupyratio = []
        for ann in sorted_anns:
            m = ann['segmentation']
            if isinstance(m, np.ndarray) and m.dtype == bool:
                m = mask_utils.encode(np.asfortranarray(m))
            elif isinstance(m, dict) and 'counts' in m and 'size' in m:
                pass  # Already in RLE format
            else:
                print("Invalid segmentation format:", m)
                continue
            
            mask = mask_utils.decode(m)
            contours, hierarchy = cv2.findContours(mask.astype(np.uint8), cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
            contours = [np.squeeze(contour) for contour in contours] # Convert contours to the correct shape
            contours = [np.atleast_2d(contour) for contour in contours]
            for c in contours:
                resized_c = []
                for x, y in c:
                    resized_c.append([int(x / ratio), int(y / ratio)])
                all_contours.append(np.array(resized_c))
        return all_contours
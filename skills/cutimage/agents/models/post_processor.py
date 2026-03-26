import logging
import numpy as np
import cv2
import torch
import torchvision
import torchvision.ops as ops

class PostProcesser:

    def __init__(self, sam_occupy_ratio=0.85, ocr_sam_iou_threshold=0.3, model_input_size=(512, 1024), debug=False):
        self._sam_occupy_ratio = sam_occupy_ratio
        self._ocr_sam_iou_threshold = ocr_sam_iou_threshold
        self._model_input_size = model_input_size
        self._debug = debug
        logging.info(f"int PostProcesser, sam_occupy_ratio={self._sam_occupy_ratio}, ocr_sam_iou_threhold={self._ocr_sam_iou_threshold}, model_input_size={self._model_input_size}, debug={self._debug}")

    def contour_intersect(self, original_image, cid1, contour1, box1, cid2, contour2, box2):
        blank = np.zeros(original_image.shape[0:2])
        image1 = cv2.drawContours(blank.copy(), contour1, 0, 1)
        image2 = cv2.drawContours(blank.copy(), contour2, 0, 1)
        intersection = np.logical_and(image1, image2)
        blank2 = np.zeros(original_image.shape[0:2])
        cv2.drawContours(blank2, contour1, 0, 255)
        return intersection.any()

    def get_overlap_contours(self, image, cid, cur_contour, cur_box, target_contours, target_boxes):
        intersected_contours = []
        for tid, (target_contour, target_box) in enumerate(zip(target_contours, target_boxes)):
            # 先看box粒度有没overlap
            A = [cur_box[0], cur_box[1], cur_box[0] + cur_box[2], cur_box[1] + cur_box[3]]
            B = [target_box[0], target_box[1], target_box[0] + target_box[2], target_box[1] + target_box[3]]
            iou = torchvision.ops.box_iou(torch.Tensor(A)[None, :], torch.Tensor(B)[None, :])
            box_intersected = False
            if iou > self._ocr_sam_iou_threshold:
                box_intersected = True
            if not box_intersected:
                continue
            target_contour = np.squeeze(target_contour, axis=1)[None, :, :]
            intersected = self.contour_intersect(image, cid, [cur_contour], A, tid, target_contour, B)
            if intersected:
                intersected_contours.append(target_contour)
                break
        return intersected_contours
    
    '''
        TODO
    '''
    def get_region_charactor_size(self, bounding_rect, character_sizes):
        pass
        return 0.

    def process(self, task_id, image, vlm_result, ocr_result, 
                    sam_masks, sam_contours, table_boxes, target_contour, result_path=None):
        # process ocr result
        image_draw = image.copy()
        vlm_bounding_boxes = []
        if vlm_result is not None:
            for i, box in enumerate(vlm_result):
                # 将box转换为cv2.boundingRect格式 (x, y, width, height)
                if len(box) == 4:  # 确保box有4个元素 [x, y, width, height]
                    logging.info(f"vlm_bounding_boxes{i}: {box}, task_id={task_id}")
                    vlm_bounding_boxes.append(box)
                else:
                    # 如果box格式不是标准的boundingRect格式，进行转换
                    if len(box) == 2:  # 如果是两个点 [top_left, bottom_right]
                        x, y = box[0]
                        w, h = box[1][0] - box[0][0], box[1][1] - box[0][1]
                        converted_box = [x, y, w, h]
                        vlm_bounding_boxes.append(converted_box)
                    else:
                        # 其他格式，尝试直接使用
                        vlm_bounding_boxes.append(box)
                cv2.rectangle(image_draw, (box[0], box[1]), (box[0] + box[2], box[1] + box[3]), (255, 0, 0), 1)
                cv2.putText(image_draw, f"VLM {i}", (box[0], box[1]), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)
        ocr_bounding_boxes = []
        if ocr_result is not None:
            pallate = np.zeros(image.shape[:2], dtype=np.uint8)
            character_sizes = []
            for line in ocr_result:
                pts = np.array(line["box"], np.int32)
                rect = cv2.minAreaRect(pts)
                # (center(x,y), (width, height), angle of rotation)
                character_sizes.append(rect)
                cv2.fillPoly(pallate, [pts], 255)
            kernel_size = int(min(image.shape[0] * 0.01, 9))
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (kernel_size, kernel_size))
            pallate = cv2.dilate(pallate, kernel)
            ocr_contours, hierarchy = cv2.findContours(pallate, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
            ocr_charactor_sizes = []
            for contour in ocr_contours:
                rect = cv2.minAreaRect(contour)
                box = cv2.boxPoints(rect)
                box = np.int0(box)
                bounding_rect = cv2.boundingRect(contour)
                ocr_bounding_boxes.append(bounding_rect)
                charator_size = self.get_region_charactor_size(bounding_rect, character_sizes)
                ocr_charactor_sizes.append(charator_size)
                if len(box) > 0:
                    cv2.drawContours(image_draw, [box], -1, (0, 0, 255), 3)
        
        sam_bounding_boxes = []
        # process sam result
        if sam_contours is not None:
            #logging.info(f"sam_contours: {len(sam_contours)}")
            for cid, contour in enumerate(sam_contours):
                if len(contour) < 2:
                    continue
                rect = cv2.minAreaRect(contour)
                bounding_rect = cv2.boundingRect(contour)
                box = cv2.boxPoints(rect)
                box = np.int0(box)
                if len(box) > 0:
                    contour_area = cv2.contourArea(contour)
                    box_area = cv2.contourArea(box)
                    occupy_ratio = contour_area / (box_area + 0.0001)
                    box2all_ratio = box_area / float(image.shape[0] * image.shape[1])
                    # 过滤太大的框
                    if box2all_ratio > self._sam_occupy_ratio:
                        logging.info(f"box={box}, sam_bounding_box2all_ratio={box2all_ratio} is larger than {self._sam_occupy_ratio}, skip")
                        continue
                    #overlap_contours = self.get_overlap_contours(image, cid, contour, bounding_rect, ocr_contours, ocr_bounding_boxes)
                    # TODO 
                    #if occupy_ratio > self._sam_occupy_ratio and len(overlap_contours) > 0:
                    if True:
                        #cv2.drawContours(image_draw, [box], -1, (0, 255, 0), 3)
                        sam_bounding_boxes.append(bounding_rect)
        
        if self._ocr_sam_iou_threshold > 0:
            # 对两种bounding box进行nms
            if len(ocr_bounding_boxes) > 0 or len(sam_bounding_boxes) > 0:
                # 合并两种bounding box
                all_boxes = []
                # 添加OCR bounding boxes
                for i, box in enumerate(ocr_bounding_boxes):
                    all_boxes.append(box)
                
                # 添加SAM bounding boxes
                for i, box in enumerate(sam_bounding_boxes):
                    all_boxes.append(box)

                # 执行NMS
                boxes = torch.tensor(all_boxes, dtype=torch.float32)
                scores = torch.ones(len(all_boxes), dtype=torch.float32)
                keep_indices = ops.nms(boxes, scores, iou_threshold=self._ocr_sam_iou_threshold)

                # 保留NMS后的结果
                # 更新bounding boxes
                ocr_bounding_boxes = [all_boxes[idx] for idx in keep_indices if idx < len(ocr_bounding_boxes)]
                sam_bounding_boxes = [all_boxes[idx] for idx in keep_indices if idx >= len(ocr_bounding_boxes)]
                
                # 渲染OCR bounding boxes (红色)
                for i, box in enumerate(ocr_bounding_boxes):
                    cv2.rectangle(image_draw, (box[0], box[1]), (box[0] + box[2], box[1] + box[3]), (255, 0, 0), 1)
                    cv2.putText(image_draw, f"OCR {i}", (box[0], box[1]), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)
        
                # 渲染SAM bounding boxes (蓝色)
                for i, box in enumerate(sam_bounding_boxes):
                    cv2.rectangle(image_draw, (box[0], box[1]), (box[0] + box[2], box[1] + box[3]), (0, 0, 255), 1)
                    cv2.putText(image_draw, f"SAM {i}", (box[0], box[1]), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
                
        if table_boxes is not None:
            for bid, box in enumerate(table_boxes):
                cv2.rectangle(image_draw, (box[0], box[1]), (box[0] + box[2], box[1] + box[3]), (255, 0, 0), 5)
                cv2.putText(image_draw, f"TABLE {bid}", (box[0], box[1]), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)

        if target_contour is not None:
            cv2.drawContours(image_draw, target_contour, -1, (0, 255, 0), 5)
            cv2.putText(image_draw, f"target_contour", (target_contour[0][0][0], target_contour[0][0][1]), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
        
        # 如果有vlm输出就用vlm输出的
        if vlm_result is not None and len(vlm_bounding_boxes) > 0:
            logging.info(f"use vlm bounding boxes: {len(vlm_bounding_boxes)}, task_id={task_id}")
            refined_boundingboxes = []
            refined_boundingboxes.extend(vlm_bounding_boxes)
        else:
            refined_boundingboxes = []
            refined_boundingboxes.extend(ocr_bounding_boxes)    
            refined_boundingboxes.extend(sam_bounding_boxes)
            # refined_boundingboxes进行聚类，以适应下有多模态模型的输入大小
            if True:
                refined_boundingboxes = self.cluster_boundingboxes(refined_boundingboxes, image.shape[:2])
            refined_boundingboxes = self.refined_boundingboxes(refined_boundingboxes, image.shape[:2]) 
        for bid, box in enumerate(refined_boundingboxes):
            cv2.rectangle(image_draw, (box[0], box[1]), (box[0] + box[2], box[1] + box[3]), (255, 128, 0), 5)
        
        # 如果debug模式，则保存图片
        if result_path is not None and self._debug:
            cv2.imwrite(result_path, image_draw)

        return refined_boundingboxes
    
    def refined_boundingboxes(self, boundingboxes, original_image_size=(1080, 1920)):
        """
        将boundingboxes画在大小为original_image_size的图片上，kernel=5的膨胀操作，
        然后重新拉取contour，以及获取对应的boundingbox
        """
        if not boundingboxes:
            return []
        
        # 创建空白图片
        height, width = original_image_size
        mask = np.zeros((height, width), dtype=np.uint8)
        
        # 将所有bounding boxes画在mask上
        for box in boundingboxes:
            x, y, w, h = box
            # 确保坐标在图片范围内
            x1, y1 = max(0, x), max(0, y)
            x2, y2 = min(width, x + w), min(height, y + h)
            if x2 > x1 and y2 > y1:
                mask[y1:y2, x1:x2] = 255
        
        # 使用kernel=5进行膨胀操作
        kernel = np.ones((5, 5), np.uint8)
        dilated_mask = cv2.dilate(mask, kernel, iterations=1)
        
        # 查找轮廓
        contours, _ = cv2.findContours(dilated_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # 获取每个轮廓的bounding box
        refined_boxes = []
        for contour in contours:
            # 计算轮廓的bounding rectangle
            x, y, w, h = cv2.boundingRect(contour)
            refined_boxes.append([x, y, w, h])
        
        return refined_boxes

    
    '''
        聚类bounding boxes
        boundingboxes: list of bounding boxes, each bounding box is a list of [x, y, w, h]
    '''
    def cluster_boundingboxes(self, boundingboxes, original_image_size=(1080, 1920)):
        logging.info(f"start to cluster_boundingboxes: original_image_size={original_image_size}")
        cluster_boxes = []
        if not boundingboxes:
            return cluster_boxes

        # 将boundingboxes转换为numpy数组便于处理
        boxes = np.array(boundingboxes)
        
        # 检查每个框的大小，如果单独一个框就比模型输入大小大了，则单独作为一个类别
        target_height, target_width = self._model_input_size
        large_boxes = []
        small_boxes = []
        
        for i, box in enumerate(boxes):
            x, y, w, h = box
            # 如果框的宽度或高度超过模型输入大小，则单独处理
            if w > target_width or h > target_height:
                large_boxes.append(box)
            else:
                small_boxes.append(i)  # 保存索引
        
        # 将大框直接加入结果
        cluster_boxes.extend(large_boxes)
        
        # 如果没有小框需要聚类，直接返回
        if not small_boxes:
            return cluster_boxes
        
        # 获取需要聚类的小框
        small_boxes_array = boxes[small_boxes]
        
        # 计算每个小框的中心点
        centers = np.column_stack([
            small_boxes_array[:, 0] + small_boxes_array[:, 2] / 2,  # x center
            small_boxes_array[:, 1] + small_boxes_array[:, 3] / 2   # y center
        ])
        
        # 使用K-means聚类，聚类数量基于图片大小和模型输入大小
        original_height, original_width = original_image_size
        
        # 估算需要的聚类数量
        height_ratio = original_height / target_height
        width_ratio = original_width / target_width
        estimated_clusters = max(1, int(height_ratio * width_ratio))
        
        # 限制聚类数量，避免过多小区域
        max_clusters = min(estimated_clusters, len(small_boxes_array))
        
        if max_clusters == 1:
            # 如果只需要一个聚类，直接返回覆盖所有小框的大框
            min_x = np.min(small_boxes_array[:, 0])
            min_y = np.min(small_boxes_array[:, 1])
            max_x = np.max(small_boxes_array[:, 0] + small_boxes_array[:, 2])
            max_y = np.max(small_boxes_array[:, 1] + small_boxes_array[:, 3])
            
            cluster_boxes.append([min_x, min_y, max_x - min_x, max_y - min_y])
        else:
            # 使用K-means聚类
            from sklearn.cluster import KMeans
            
            kmeans = KMeans(n_clusters=max_clusters, random_state=42, n_init=10)
            cluster_labels = kmeans.fit_predict(centers)
            
            # 为每个聚类生成覆盖该聚类所有box的bounding box
            for cluster_id in range(max_clusters):
                cluster_mask = cluster_labels == cluster_id
                if not np.any(cluster_mask):
                    continue
                    
                cluster_boxes_array = small_boxes_array[cluster_mask]
                
                # 计算该聚类的边界框
                min_x = np.min(cluster_boxes_array[:, 0])
                min_y = np.min(cluster_boxes_array[:, 1])
                max_x = np.max(cluster_boxes_array[:, 0] + cluster_boxes_array[:, 2])
                max_y = np.max(cluster_boxes_array[:, 1] + cluster_boxes_array[:, 3])
                
                cluster_boxes.append([min_x, min_y, max_x - min_x, max_y - min_y])
            
        # 将boundingboxes转换为numpy数组便于处理
        boxes = np.array(boundingboxes)
        
        # 计算每个box的中心点
        centers = np.column_stack([
            boxes[:, 0] + boxes[:, 2] / 2,  # x center
            boxes[:, 1] + boxes[:, 3] / 2   # y center
        ])
        
        # 使用K-means聚类，聚类数量基于图片大小和模型输入大小
        target_height, target_width = self._model_input_size
        original_height, original_width = original_image_size
        
        # 估算需要的聚类数量
        height_ratio = original_height / target_height
        width_ratio = original_width / target_width
        estimated_clusters = max(1, int(height_ratio * width_ratio))
        
        # 限制聚类数量，避免过多小区域
        max_clusters = min(estimated_clusters, len(boundingboxes))
        
        if max_clusters == 1:
            # 如果只需要一个聚类，直接返回覆盖所有box的大框
            min_x = np.min(boxes[:, 0])
            min_y = np.min(boxes[:, 1])
            max_x = np.max(boxes[:, 0] + boxes[:, 2])
            max_y = np.max(boxes[:, 1] + boxes[:, 3])
            
            cluster_boxes.append([min_x, min_y, max_x - min_x, max_y - min_y])
        else:
            # 使用K-means聚类
            from sklearn.cluster import KMeans
            
            kmeans = KMeans(n_clusters=max_clusters, random_state=42, n_init=10)
            cluster_labels = kmeans.fit_predict(centers)
            
            # 为每个聚类生成覆盖该聚类所有box的bounding box
            for cluster_id in range(max_clusters):
                cluster_mask = cluster_labels == cluster_id
                if not np.any(cluster_mask):
                    continue
                    
                cluster_boxes_array = boxes[cluster_mask]
                
                # 计算该聚类的边界框
                min_x = np.min(cluster_boxes_array[:, 0])
                min_y = np.min(cluster_boxes_array[:, 1])
                max_x = np.max(cluster_boxes_array[:, 0] + cluster_boxes_array[:, 2])
                max_y = np.max(cluster_boxes_array[:, 1] + cluster_boxes_array[:, 3])
                
                # 添加一些padding，确保不会切碎box
                padding = 10
                min_x = max(0, min_x - padding)
                min_y = max(0, min_y - padding)
                max_x = min(original_width, max_x + padding)
                max_y = min(original_height, max_y + padding)
                
                cluster_boxes.append([min_x, min_y, max_x - min_x, max_y - min_y])
        
        logging.info(f"clustered {len(boundingboxes)} boxes into {len(cluster_boxes)} clusters")
        return cluster_boxes
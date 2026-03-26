import cv2
import numpy as np
import logging

class DottedLineDetector:

    def __init__(self, enable_visualization=False) -> None:
        self._enable_visualization = enable_visualization

    def infer(self, image_data, ratio, page_tag=None):
        target_contour = None
        gray_image = cv2.cvtColor(image_data, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray_image, (5, 5), 0)
        edges = cv2.Canny(blurred, 50, 150)
        kernel_size = int(image_data.shape[0] * 0.01)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (kernel_size, kernel_size))
        edges = cv2.dilate(edges, kernel)
        contours, hierarchy = cv2.findContours(edges.astype(np.uint8), cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        contours = [(np.squeeze(contour), cv2.contourArea(contour)) for contour in contours] # Convert contours to the correct shape
        sorted_contours = sorted(contours, key=lambda x: -x[1])
        
        if len(sorted_contours) > 0 and sorted_contours[0][1] > (image_data.shape[0] * image_data.shape[1] * 0.5):
            tc = []
            for x, y in sorted_contours[0][0]:
                tc.append([int(x / ratio), int(y / ratio)])
            target_contour = [np.array(tc)]
            if self._enable_visualization:
                blank2 = np.zeros(image_data.shape[0:2])
                cv2.drawContours(blank2, target_contour, 0, 255)
                cv2.imwrite(f'./datas/target/{page_tag}_contour.jpg', blank2)
        return target_contour
IMAGE_CUT_PROMPT = {}

IMAGE_CUT_PROMPT['image_cut_v1'] = """
请对上传的玩具外包装图进行图像分割，识别并切分为6个面（通常为盒子的左侧面、右侧面、正面、背面、上面、下面）。依据图中显著的实线/虚线分割线与常见包装盒的展开图布局，确定每一面的位置。

要求：
1. 对每个面输出一个检测框，格式采用 YOLO 坐标格式：[x_center, y_center, width, height]，所有数值归一化（相对于图像宽高）。
2. 返回一个合法有效的 JSON 对象，结构如下：
   {
     "reason": "解释你如何根据视觉结构判断出这6个面的位置",
     "boundingboxes": [
       [x_center, y_center, width, height],
       ...
     ]
   }
3. JSON 中不得包含注释、额外文字或解释，输出中只包含 JSON。
4. boundingboxes 数组长度必须为6，对应6个不同面。
"""
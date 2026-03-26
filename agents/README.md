# 如何安装
```
pip install git+https://github.com/facebookresearch/segment-anything.git
pip install paddlepaddle -i https://pypi.tuna.tsinghua.edu.cn/simple
pip install "paddleocr>=2.0.1" -i https://pypi.tuna.tsinghua.edu.cn/simple
pip install pycocotools -i https://pypi.tuna.tsinghua.edu.cn/simple
pip install ultralytics -i https://pypi.tuna.tsinghua.edu.cn/simple
pip install scikit-learn -i https://pypi.tuna.tsinghua.edu.cn/simple
pip install -i https://pypi.tuna.tsinghua.edu.cn/simple/ pdf2image
apt-get update && apt-get install -y libgl1-mesa-glx
apt-get update && apt-get install -y libglib2.0-0
apt update && apt install -y poppler-utils
```

# 如何测试
```
cd sgs_toy_mvp
# 测试切图
PYTHONPATH=`pwd` python agents/image_cut/image_cut_agent.py
# 测试图片类型分类
PYTHONPATH=`pwd` python agents/object_classify/object_classify_agent.py
# 测试规则判定
PYTHONPATH=`pwd` python agents/rule_check/rule_check_agent.py

```
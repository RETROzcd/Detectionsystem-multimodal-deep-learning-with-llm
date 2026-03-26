#! encoding: utf-8

class ObjectClassifyRequest:
    '''
    定义对象分类的输入数据
    输入数据包括：
    1. 产品图片
    2. 包装图片
    3. 手动图片
    4. 其他信息
    5. 模型名称
    '''
    def __init__(self, task_id:str, 
                product_images:list[str], package_images:list[str], manual_images:list[str],
                other_info: str):
        self.task_id = task_id
        self.product_images = product_images
        self.package_images = package_images
        self.manual_images = manual_images
        self.other_info = other_info
        
    
    def get_task_id(self):
        return self.task_id
    
    def get_product_images(self):
        return self.product_images

    def get_package_images(self):
        return self.package_images

    def get_manual_images(self):
        return self.manual_images

    def get_other_info(self):
        return self.other_info

    def __str__(self):
        return f"Task ID: {self.task_id}, Product Images: {self.product_images}, Package Images: {self.package_images}, Manual Images: {self.manual_images}, Other Info: {self.other_info}"



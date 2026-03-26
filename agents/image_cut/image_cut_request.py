#! encoding: utf-8

class ImageCutRequest:
    def __init__(self, task_id:str, product_images:list[str], package_images:list[str], manual_images:list[str], work_dir:str):
        self.task_id = task_id
        self.product_images = product_images  # List of product image paths
        self.package_images = package_images  # List of package image paths
        self.manual_images = manual_images   # List of manual image paths
        self.work_dir = work_dir
    
    def get_task_id(self):
        return self.task_id
        
    def get_product_images(self):
        return self.product_images
    
    def get_package_images(self):
        return self.package_images
    
    def get_manual_images(self):
        return self.manual_images
    
    def get_work_dir(self):
        return self.work_dir

    def __str__(self):
        return f"Task ID: {self.task_id}, Product Images: {self.product_images}, Package Images: {self.package_images}, Manual Images: {self.manual_images}, Work Dir: {self.work_dir}"

#! encoding: utf-8

class ImageCutResponse:
    '''
    This class is responsible for the response of image cut.
    key: original image path
    value: cutted image paths
    '''
    def __init__(self):
        self.cutted_product_images = {}
        self.cutted_package_images = {}
        self.cutted_manual_images = {}

    '''
    添加产品图片的切割信息
    '''
    def add_cutted_product_image(self, original_image_path:str, cutted_image_paths:list[str]):
        self.cutted_product_images[original_image_path] = cutted_image_paths

    '''
    添加包装图片的切割信息
    '''
    def add_cutted_package_image(self, original_image_path:str, cutted_image_paths:list[str]):
        self.cutted_package_images[original_image_path] = cutted_image_paths

    '''
    添加说明书图片的切割信息
    '''
    def add_cutted_manual_image(self, original_image_path:str, cutted_image_paths:list[str]):
        self.cutted_manual_images[original_image_path] = cutted_image_paths

    def get_cutted_product_images(self):
        return self.cutted_product_images
    
    def get_cutted_package_images(self):
        return self.cutted_package_images
    
    def get_cutted_manual_images(self):
        return self.cutted_manual_images

    def __str__(self):
        return f"Cutted Product Images: {self.cutted_product_images}, Cutted Package Images: {self.cutted_package_images}, Cutted Manual Images: {self.cutted_manual_images}"

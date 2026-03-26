'''
定义对象分类的输出数据 
'''

class ObjectClassifyResponse:
    '''
    定义对象分类的输出数据
    输出数据包括：
    1. 玩具类别
    2. 产品特性
    3. 细分特性
    '''

    def __init__(self, status: bool, message: str, 
            toy_category: set[str], product_features: set[str], sub_features: set[str], reason: str=""):
        self.status = status
        self.message = message
        self.toy_category = toy_category
        self.product_features = product_features
        self.sub_features = sub_features
        self.reason = reason
    
    def get_status(self):
        return self.status
    
    def get_message(self):
        return self.message

    def get_toy_category(self):
        return self.toy_category

    def get_product_features(self):
        return self.product_features
    
    def get_sub_features(self):
        return self.sub_features

    def get_reason(self):
        return self.reason

    def __str__(self):
        return f"Status: {self.status}, Message: {self.message}, Toy Category: {self.toy_category}, Product Features: {self.product_features}, Sub Features: {self.sub_features}, reason: {self.reason}"

if __name__ == "__main__":
    response = ObjectClassifyResponse(True, "success", toy_category={"玩具1", "玩具2"}, product_features={"玩具类别1", "玩具类别2"}, sub_features={"x1", "x2"})
    print(response.get_toy_category())
    print(response.get_product_features())
    print(response.get_sub_features())

    
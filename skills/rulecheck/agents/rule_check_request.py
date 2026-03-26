#! encoding: utf-8

from agents.rule_check.rule import Rule

class RuleCheckRequest:
    '''
    定义规则检查的输入数据
    输入数据包括：
    1. 任务ID
    2. 是否启用切割后的图片
    ***【图片信息】***
    3. 产品图片
    4. 包装图片
    5. 说明图片
    6. 切割后的产品图片
    7. 切割后的包装图片
    8. 切割后的说明书图片
    ***【图片信息】***
    *** 【预打标信息】***
    9. 玩具类别
    10. 产品特性
    11. 细分特性
    12. 设计年龄范围
    *** 【预打标信息】***
    13. 其他信息
    14. 模型名称
    '''
    def __init__(self, task_id:str, enable_cutted_images:bool,
                     product_images:list[str], package_images:list[str], manual_images:list[str],   
                     cutted_product_images:dict[str, list[str]], cutted_package_images:dict[str, list[str]], cutted_manual_images:dict[str, list[str]],
                     toy_category: set[str], product_features: set[str], sub_features: set[str], design_age_range: str,
                     other_info:str, 
                     ):
        self.task_id = task_id
        self.enable_cutted_images = enable_cutted_images
        self.product_images = product_images
        self.package_images = package_images
        self.manual_images = manual_images
        self.cutted_product_images = cutted_product_images
        self.cutted_package_images = cutted_package_images
        self.cutted_manual_images = cutted_manual_images
        self.toy_category = toy_category
        self.product_features = product_features
        self.sub_features = sub_features
        self.design_age_range = design_age_range
        self.other_info = other_info
        # 以章节信息为组，存储规则  
        self.rules_by_group_id = {}
        self.rules = []

    def to_json(self):
        """
        将 RuleCheckRequest 对象转为 JSON 可序列化的 dict
        """
        return {
            "task_id": self.task_id,
            "enable_cutted_images": self.enable_cutted_images,
            "product_images": self.product_images,
            "package_images": self.package_images,
            "manual_images": self.manual_images,
            "cutted_product_images": self.cutted_product_images,
            "cutted_package_images": self.cutted_package_images,
            "cutted_manual_images": self.cutted_manual_images,
            "toy_category": list(self.toy_category) if isinstance(self.toy_category, set) else self.toy_category,
            "product_features": list(self.product_features) if isinstance(self.product_features, set) else self.product_features,
            "sub_features": list(self.sub_features) if isinstance(self.sub_features, set) else self.sub_features,
            "design_age_range": self.design_age_range,
            "other_info": self.other_info,
            "rules": [rule.to_json() if hasattr(rule, "to_json") else rule for rule in self.rules]
        }

    @classmethod
    def from_json(cls, data, filter_keyword=None):
        """
        从 dict/json 恢复 RuleCheckRequest 对象
        """
        # 兼容 set 类型字段
        toy_category = set(data.get("toy_category", []))
        product_features = set(data.get("product_features", []))
        sub_features = set(data.get("sub_features", []))
        # 兼容图片字段
        product_images = data.get("product_images", [])
        package_images = data.get("package_images", [])
        manual_images = data.get("manual_images", [])
        cutted_product_images = data.get("cutted_product_images", {})
        cutted_package_images = data.get("cutted_package_images", {})
        cutted_manual_images = data.get("cutted_manual_images", {})
        # 其他字段
        task_id = data.get("task_id")
        enable_cutted_images = data.get("enable_cutted_images", False)
        design_age_range = data.get("design_age_range", "")
        other_info = data.get("other_info", "")

        obj = cls(
            task_id=task_id,
            enable_cutted_images=enable_cutted_images,
            product_images=product_images,
            package_images=package_images,
            manual_images=manual_images,
            cutted_product_images=cutted_product_images,
            cutted_package_images=cutted_package_images,
            cutted_manual_images=cutted_manual_images,
            toy_category=toy_category,
            product_features=product_features,
            sub_features=sub_features,
            design_age_range=design_age_range,
            other_info=other_info
        )
        # 还原 rules
        rules_data = data.get("rules", [])
        for rule_data in rules_data:
            # 假设 Rule 有 from_json 方法，否则直接传入 Rule(**rule_data)
            if hasattr(Rule, "from_json"):
                rule = Rule.from_json(rule_data)
            else:
                rule = Rule(**rule_data)
            if filter_keyword is not None:
                audit_content = rule.get_audit_content()
                if audit_content is not None and filter_keyword in audit_content:
                    obj.add_rule(rule)
            else:
                obj.add_rule(rule)
        return obj
    
    '''
    添加规则
    '''
    def add_rule(self, rule:Rule):
        group_id = rule.get_group_id()
        if group_id not in self.rules:
            self.rules_by_group_id[group_id] = []
        self.rules_by_group_id[group_id].append(rule)
        self.rules.append(rule)

    def set_task_id(self, task_id:str):
        self.task_id = task_id

    def get_rules(self):
        return self.rules

    def get_task_id(self):
        return self.task_id

    def get_enable_cutted_images(self): 
        return self.enable_cutted_images
    
    def get_product_images(self):
        return self.product_images
    
    def get_package_images(self):
        return self.package_images
    
    def get_manual_images(self):
        return self.manual_images
    
    def get_cutted_product_images(self):
        return self.cutted_product_images
    
    def get_cutted_package_images(self):
        return self.cutted_package_images
    
    def get_cutted_manual_images(self):
        return self.cutted_manual_images
    
    def get_toy_category(self):
        return self.toy_category
    
    def get_product_features(self):
        return self.product_features
    
    def get_sub_features(self):
        return self.sub_features 
    
    def get_design_age_range(self):
        return self.design_age_range

    def get_other_info(self):
        return self.other_info

    def __str__(self):
        return f"Task ID: {self.task_id}, Enable Cutted Images: {self.enable_cutted_images}, Product Images: {self.product_images}, Package Images: {self.package_images}, Manual Images: {self.manual_images}, Cutted Product Images: {self.cutted_product_images}, Cutted Package Images: {self.cutted_package_images}, Cutted Manual Images: {self.cutted_manual_images}, Toy Category: {self.toy_category}, Product Features: {self.product_features}, Sub Features: {self.sub_features}, Design Age Range: {self.design_age_range}, Other Info: {self.other_info}"

if __name__ == "__main__":
    request = RuleCheckRequest(task_id="123",
                               enable_cutted_images=True,
                               product_images=["product_image1", "product_image2"],
                               package_images=["package_image1", "package_image2"],
                               manual_images=["manual_image1", "manual_image2"] ,
                               cutted_product_images={"product_image1":["cutted_product_image1"], "product_image2":["cutted_product_image2"]},
                               cutted_package_images={"package_image1":["cutted_package_image1"], "package_image2":["cutted_package_image2"]},
                               cutted_manual_images={"manual_image1":["cutted_manual_image1"], "manual_image2":["cutted_manual_image2"]},
                               toy_category={"玩具类别1", "玩具类别2"},
                               product_features={"产品特性1", "产品特性2"},
                               sub_features={"细分特性1", "细分特性2"},
                               design_age_range="设计年龄范围", 
                               other_info="other_info"
                               )

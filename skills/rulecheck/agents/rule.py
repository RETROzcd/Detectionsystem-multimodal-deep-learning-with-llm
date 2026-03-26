'''
Rule类

 {
    "chapter":"章节 01 General Labeling requirements",
    "title":"标题 One Time Use Products Fair Packaging and Labeling Act or All Other Products.  Uniform Packaging and Labeling Regulations",
    "":"F.P. & L. Act (16 CFR 500) OR NIST Uniform Laws and Regulations  Handbook 130",
    "rule_determination":[
      {
        "title":"",
        "pics":["图片路径","图片路径"],
        "feedback":{
          "pass":true/fasle,
          "llm_response":"",
          "llm_prompt":""
        }
      },
    ]
  }

'''
class Rule:
    
    '''
    定义规则类，用于存储和管理规则相关信息
    包含以下属性：
    - group_id: 规则组ID(以章节信息为组)
    - rule_id: 规则ID
    - chapter: 章节信息
    - title: 规则标题
    - method: 检查方法
    - requirements: 规则要求
    - preconditions: 前置条件
    - age_range_label: 年龄范围标签
    - audit_content: 审核内容
    - exemption_clauses: 豁免条款
    - output_requirements: 输出要求
    '''
    def __init__(self, group_id:str, rule_id:str, chapter:str, title:str, method:str, requirements:str, 
                 preconditions:str, audit_content:str, exemption_clauses:str, llm_prompt:str, age_range_label:str):
        self.group_id = group_id
        self.rule_id = rule_id
        self.chapter = chapter  
        self.title = title
        self.method = method
        self.requirements = requirements

        self.preconditions = preconditions
        # 年龄范围标签
        self.age_range_label = age_range_label
        self.audit_content = audit_content
        self.exemption_clauses = exemption_clauses
        self.llm_prompt = llm_prompt

    @classmethod
    def from_json(cls, data):
        """
        从 dict/json 恢复 Rule 对象
        """
        return cls(
            group_id=data.get("group_id", ""),
            rule_id=data.get("rule_id", ""),
            chapter=data.get("chapter", ""),
            title=data.get("title", ""),
            method=data.get("method", ""),
            requirements=data.get("requirements", ""),
            preconditions=data.get("preconditions", ""),
            audit_content=data.get("audit_content", ""),
            exemption_clauses=data.get("exemption_clauses", ""),
            llm_prompt=data.get("llm_prompt", ""),
            age_range_label=data.get("age_range_label", "")
        )
    
    def to_json(self):
        """
        将 Rule 对象转为 JSON 可序列化的 dict
        """
        return {
            "group_id": self.group_id,
            "rule_id": self.rule_id,
            "chapter": self.chapter,
            "title": self.title,
            "method": self.method,
            "requirements": self.requirements,
            "preconditions": self.preconditions,
            "audit_content": self.audit_content,
            "exemption_clauses": self.exemption_clauses,
            "llm_prompt": self.llm_prompt,
            "age_range_label": self.age_range_label
        }
    
    def get_group_id(self):
        return self.group_id

    def get_rule_id(self):
        return self.rule_id

    def get_chapter(self):
        return self.chapter

    def get_title(self):
        return self.title

    def get_method(self):
        return self.method  

    def get_requirements(self):
        return self.requirements

    def get_preconditions(self):
        return self.preconditions

    def get_age_range_label(self):
        return self.age_range_label

    def get_audit_content(self):
        return self.audit_content

    def get_exemption_clauses(self):
        return self.exemption_clauses

    def get_llm_prompt(self):
        return self.llm_prompt

    def __str__(self):
        return f"Group ID: {self.group_id}, Rule ID: {self.rule_id}, Chapter: {self.chapter}, Title: {self.title}, Method: {self.method}, Requirements: {self.requirements}, Preconditions: {self.preconditions}, Age Range Label: {self.age_range_label}, Audit Content: {self.audit_content}, Exemption Clauses: {self.exemption_clauses}, LLM Prompt: {self.llm_prompt}"

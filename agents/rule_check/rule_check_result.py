'''
一条规则的检查结果
"pass":true/fasle,
          "llm_response":"",
          "llm_prompt":""
'''
class RuleCheckResult:

    '''
    run_status: 是否运行成功
    necessity_state: 是否必要性
    message: 检查结果说明
    pics: 检查结果图片
    pass_status: 是否通过
    llm_response: 检查结果说明
    '''
    def __init__(self):
        self.run_status = True
        self.message = ""
        self.necessity_state = True
        self.necessity_reason = ""
        self.pics = []
        self.pass_status = False
        # content
        self.llm_response = ""
        self.remark = ""
        # reason
        self.reason = ""
    
    def fill(self, run_status: bool, message: str, necessity_state: bool, necessity_reason: str, pics: list, pass_status: bool, llm_response: str, reason: str=None, remark: str=None):
        self.run_status = run_status
        self.message = message
        self.necessity_state = necessity_state
        self.necessity_reason = necessity_reason
        self.pics = pics
        self.pass_status = pass_status
        self.llm_response = llm_response
        self.remark = remark
        self.reason = reason

    def to_json(self):
        """
        将 RuleCheckResult 对象转为 JSON 可序列化的 dict
        """
        return {
            "run_status": self.run_status,
            "message": self.message,
            "necessity_state": self.necessity_state,
            "necessity_reason": self.necessity_reason,
            "pics": self.pics,
            "pass_status": self.pass_status,
            "llm_response": self.llm_response
        }
    
    @classmethod
    def from_json(cls, data):
        """
        从 dict/json 恢复 RuleCheckResult 对象
        """
        obj = cls()
        obj.run_status = data.get("run_status", True)
        obj.message = data.get("message", "")
        obj.necessity_state = data.get("necessity_state", True)
        obj.necessity_reason = data.get("necessity_reason", "")
        obj.pics = data.get("pics", [])
        obj.pass_status = data.get("pass_status", False)
        obj.llm_response = data.get("llm_response", "")
        return obj

    def set_run_status(self, run_status: bool):
        self.run_status = run_status    

    def set_necessity_state(self, necessity_state: bool):
        self.necessity_state = necessity_state
    
    def set_necessity_reason(self, necessity_reason):
        self.necessity_reason = necessity_reason

    def set_pass_status(self, pass_status: bool):
        self.pass_status = pass_status

    def set_llm_response(self, llm_response: str):
        self.llm_response = llm_response

    def set_remark(self, remark: str):
        self.remark = remark

    def set_reason(self, reason: str):
        self.reason = reason

    def get_run_status(self):
        return self.run_status  

    def get_necessity_state(self):
        return self.necessity_state

    def get_necessity_reason(self):
        return self.necessity_reason
    
    def get_message(self):
        return self.message
    
    '''
        添加命中的结果图片
    '''
    def add_pic(self, pic):
        if pic is not None:
            if isinstance(pic, list):
                self.pics.extend(pic)
            else:
                self.pics.append(pic)

    def get_pics(self):
        return self.pics

    def get_check_result_pics(self):
        return self.pics

    def get_pass_status(self):
        return self.pass_status
    
    def get_llm_response(self):
        return self.llm_response
    
    def get_remark(self):
        return self.remark

    def get_reason(self):
        return self.reason

    def __str__(self):
        return f"run_status: {self.run_status}, message: {self.message}, necessity_state: {self.necessity_state}, necessity_reason: {self.necessity_reason}, pics: {self.pics}, pass_status: {self.pass_status}, llm_response: {self.llm_response}"

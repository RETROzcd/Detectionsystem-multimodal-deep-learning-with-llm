from agents.rule_check.rule import Rule
from agents.rule_check.rule_check_result import RuleCheckResult

'''
定义规则检查的输出数据 
'''
class RuleCheckResponse:
    '''
    定义规则检查的输出数据
    输出数据包括：
    1. 玩具类别
    2. 产品特性
    3. 细分特性
    '''

    def __init__(self, status: bool, message: str, task_id: str):
        self.run_status = status
        self.message = message
        self.task_id = task_id
        # 每一项有一个检查结果，检查结果包括：
        self.check_results = []
        # rule_id -> (rule, list[check_result])
        self.sub_check_results = {}

    def add_check_result(self, rule: Rule, check_result: RuleCheckResult, idx: int):
        self.check_results.append({
            "rule": rule,
            "check_result": check_result,
            "idx": idx
        })

    def add_sub_check_result(self, rule: Rule, check_result: RuleCheckResult, idx: int, sub_images_files: list[str]):
        if idx not in self.sub_check_results:
            self.sub_check_results[idx] = (rule, [(sub_images_files, check_result)])
        else:
            self.sub_check_results[idx][1].append((sub_images_files, check_result))
    
    def get_sub_check_results(self):
        return self.sub_check_results

    def to_json(self):
        """
        将 RuleCheckResponse 对象转为 JSON 可序列化的 dict
        """
        return {
            "run_status": self.run_status,
            "message": self.message,
            "task_id": self.task_id,
            "check_results": [
                {
                    "rule": rule.to_json() if hasattr(rule, "to_json") else rule,
                    "check_result": check_result.to_json() if hasattr(check_result, "to_json") else check_result,
                    "idx": idx
                }
                for item in self.check_results
                for rule, check_result, idx in [(item["rule"], item["check_result"], item["idx"])]
            ]
        }

    @classmethod
    def from_json(cls, data):
        """
        从 dict/json 恢复 RuleCheckResponse 对象
        """
        status = data.get("run_status", True)
        message = data.get("message", "")
        task_id = data.get("task_id", "")
        obj = cls(status, message, task_id)
        check_results_data = data.get("check_results", [])
        for item in check_results_data:
            rule_data = item.get("rule")
            check_result_data = item.get("check_result")
            idx = item.get("idx", 0)
            # 反序列化 Rule 和 RuleCheckResult
            if hasattr(Rule, "from_json"):
                rule = Rule.from_json(rule_data)
            else:
                rule = Rule(**rule_data)
            if hasattr(RuleCheckResult, "from_json"):
                check_result = RuleCheckResult.from_json(check_result_data)
            else:
                check_result = RuleCheckResult(**check_result_data)
            obj.add_check_result(rule, check_result, idx)
        return obj
     
    def get_task_id(self):
        return self.task_id

    def set_run_status(self, status: bool):
        self.run_status = status

    def set_message(self, message: str):
        self.message = message

    def get_run_status(self):
        return self.run_status

    def get_message(self):
        return self.message 
    
    def get_check_results(self):
        # 按照idx排序
        self.check_results.sort(key=lambda x: x['idx'])
        return self.check_results
    
    def __str__(self):
        check_results_str = "; ".join([
            f"Rule: {result['rule']}, Check Result: {result['check_result']}"
            for result in self.check_results
        ])
        return f"Run_status: {self.run_status}, Message: {self.message}, Check Results: {check_results_str}"



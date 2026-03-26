class RedisCategoryAndFeatureData:
    def __init__(self):
        self.toy_category = []
        self.features = []
        self.sub_features_chemical_experiment_kit_with_reactive_substances = []
        self.sub_features_battery_powered_toy = []

class RedisRuleCheckResult:
    def __init__(self):
        self.chapter = ""
        self.title = ""
        self.method = ""
        self.requirements = ""
        self.audit_content = ""
        self.llm_prompt = ""
        self.pics = []
        self.pass_status = False
        self.necessity_state = True
        self.necessity_reason = ""
        self.llm_response = ""
        self.manual_is_error = False
        self.manual_correct_conclusion = ""
        self.manual_error_reason = ""
        self.rule_file_path = ""

class RedisData:
    def __init__(self):
        self.ai_category_and_feature_data = RedisCategoryAndFeatureData()
        self.manual_category_and_feature_data = RedisCategoryAndFeatureData()
        self.rule_check_results = None #规则检查结果
        self.rule_file_path = "" #规则文件路径
        self.rule_check_result = None #规则检查结果
        self.preprocessed_data = None #预处理数据
        self.image_cut_response = None #图片切割响应
        self.object_classify_response = None #对象分类响应
        self.user_input_data = None #用户输入数据
        self.work_dir_image_directories = None #工作目录图片目录
        self.rule_check_response = None #规则检查响应
        self.db_task_id = None
        self.db_rule_check_response_id = None
        self.task_overview = None
    




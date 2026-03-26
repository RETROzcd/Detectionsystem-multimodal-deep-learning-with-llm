from datetime import datetime
from typing import Optional
class ExcelNameGenerator:
    def __init__(self, redis_util, prefix: str = "TLR"):
        self.redis_util = redis_util
        self.prefix = prefix
    
    def generate_excel_name(self, session_hash: str) -> str:
        # 检查是否已存在excel_name
        if self.redis_util.exists_key("excel_name"):
            excel_name = self.redis_util.get_value("excel_name")
            return excel_name
        
        # 生成新的文件名
        today_str = datetime.now().strftime("%Y%m%d")
        key_name = f"excel_serial_{today_str}"
        
        # 检查redis
        if self.redis_util.exists_key(key_name):
            serial = int(self.redis_util.get_value(key_name)) + 1
        else:
            serial = 1
        
        #保存新的流水号到redis
        self.redis_util.set_value(key_name, str(serial).zfill(4))
        excel_name = f"{self.prefix}{today_str}{str(serial).zfill(4)}.xlsx"
        self.redis_util.set_value("excel_name", excel_name)
        return excel_name
    
    def get_default_excel_name(self) -> str:
        return "结果.xlsx"
    def reset_excel_name(self) -> None:
        #重置
        if self.redis_util.exists_key("excel_name"):
            self.redis_util.delete_key("excel_name")

def create_excel_name_generator(redis_util, prefix: str = "TLR") -> ExcelNameGenerator:
    """
    创建Excel文件名生成器的工厂函数
    Args:
        redis_util: Redis工具类实例
        prefix: 文件名前缀，默认为"TLR"
    Returns:
        ExcelNameGenerator: Excel文件名生成器实例
    """
    return ExcelNameGenerator(redis_util, prefix)

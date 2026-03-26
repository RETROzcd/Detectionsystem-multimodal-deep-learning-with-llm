#年龄范围重叠识别工具
import re
from typing import Optional, Tuple


class AgeRange:
    def __init__(self, value_from: Optional[float], value_to: Optional[float], 
                 from_type: str, to_type: str, unit: str):
        self.value_from = value_from
        self.value_to = value_to
        self.from_type = from_type
        self.to_type = to_type
        self.unit = unit
    
    def get_start_months(self) -> float:
        if self.value_from is None:
            return 0.0
        months = self.value_from
        if self.unit == "岁":
            months = self.value_from * 12
        return months
    
    def get_end_months(self) -> Optional[float]:
        if self.value_to is None:
            return None
        months = self.value_to
        if self.unit == "岁":
            months = self.value_to * 12
        return months
    
    def has_overlap(self, other: 'AgeRange') -> bool:
        # 转换为月数进行比较
        self_start = self.get_start_months()
        self_end = self.get_end_months()
        other_start = other.get_start_months()
        other_end = other.get_end_months()
        
        # 判断是否有重叠
        # 情况1: self有上限，other有上限
        if self_end is not None and other_end is not None:
            return self_start <= other_end and other_start <= self_end
        
        # 情况2: self有上限，other无上限
        if self_end is not None and other_end is None:
            return self_end >= other_start
        
        # 情况3: self无上限，other有上限
        if self_end is None and other_end is not None:
            return other_end >= self_start
        
        # 情况4: 都无上限
        return True
    
    def __str__(self):
        if self.from_type == "range" and self.to_type == "range":
            return f"年龄:{self.value_from}{self.unit}到{self.value_to}{self.unit}"
        elif self.from_type == "below":
            return f"年龄:{self.value_to}{self.unit}及以下"
        elif self.from_type == "above":
            return f"年龄:{self.value_from}{self.unit}及以上"
        else:
            return f"年龄:{self.value_from}{self.unit}"


class AgeRangeParser:
    def __init__(self):
        self.range_pattern = re.compile(r'年龄:(\d+(?:\.\d+)?)(岁|月)到(\d+(?:\.\d+)?)(岁|月)')
        self.above_pattern = re.compile(r'年龄:(\d+(?:\.\d+)?)(岁|月)及以上')
        self.below_pattern = re.compile(r'年龄:(\d+(?:\.\d+)?)(岁|月)及以下')
    def parse(self, age_str: str) -> Optional[AgeRange]:
        if not age_str or not age_str.strip():
            return None
        age_str = age_str.strip()
        match = self.range_pattern.match(age_str)
        if match:
            value_from = float(match.group(1))
            unit_from = match.group(2)
            value_to = float(match.group(3))
            unit_to = match.group(4)
            # 确保单位一致（如果不是，需要转换）
            if unit_from != unit_to:
                if unit_from == "岁":
                    value_from = value_from * 12
                if unit_to == "岁":
                    value_to = value_to * 12
                return AgeRange(value_from, value_to, "range", "range", "月")
            return AgeRange(value_from, value_to, "range", "range", unit_from)

        match = self.above_pattern.match(age_str)
        if match:
            value_from = float(match.group(1))
            unit = match.group(2)
            return AgeRange(value_from, None, "above", "above", unit)
        
        # 尝试匹配及以下格式
        match = self.below_pattern.match(age_str)
        if match:
            value_to = float(match.group(1))
            unit = match.group(2)
            return AgeRange(None, value_to, "below", "below", unit)
        return None


def has_age_range_overlap(str_a: str, str_b: str) -> bool:
    parser = AgeRangeParser()
    range_a = parser.parse(str_a)
    range_b = parser.parse(str_b)
    if range_a is None or range_b is None:
        return False
    return range_a.has_overlap(range_b)



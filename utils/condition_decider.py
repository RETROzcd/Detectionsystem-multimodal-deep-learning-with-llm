class ConditionDecider:
    def __init__(self):
        pass
    @staticmethod
    def decide(toy_category: list, rule_condition: str) -> bool:
        # rule_condition 
        true_conditions = ConditionDecider.check_condition_expression(toy_category, rule_condition)
        return true_conditions

    @staticmethod
    def check_condition_expression(true_conditions, expression):
        # 转为集合，提高查找效率
        satisfied_set = set(true_conditions)
        # 预处理：去除换行符，保留空格（条件内容可能包含空格）
        expr = expression.replace('\n', '').replace('\r', '').strip()
        # 定义括号/引号对
        bracket_pairs = [
            ('【', '】'),
            ('"', '"'),
            ('"', '"'),
            ('（', '）'),
            ('(', ')'),
        ]
        # 解析表达式，提取条件和操作符
        tokens = []
        i = 0
        n = len(expr)
        current_condition = ""
        
        while i < n:
            found_bracket = False
            for left, right in bracket_pairs:
                if i < n and expr[i] == left:
                    if current_condition.strip():
                        formatted_cond = "【" + current_condition.strip() + "】"
                        tokens.append(formatted_cond)
                        current_condition = ""
                    
                    # 使用栈来正确匹配嵌套括号
                    stack = [left]
                    end = i + 1
                    while end < n and stack:
                        if expr[end] == left:
                            stack.append(left)
                        elif expr[end] == right:
                            stack.pop()
                        end += 1
                    
                    if stack:
                        raise ValueError(f"表达式格式错误：缺少右侧的{right}")

                    content = expr[i+1:end-1].strip()
                    formatted_cond = "【" + content + "】"
                    tokens.append(formatted_cond)
                    i = end
                    found_bracket = True
                    break
            
            if found_bracket:
                continue

            if i < n - 1 and expr[i:i+1] in {'且', '或'}:
                if current_condition.strip():
                    formatted_cond = "【" + current_condition.strip() + "】"
                    tokens.append(formatted_cond)
                    current_condition = ""

                tokens.append(expr[i:i+1])
                i += 1
            else:
                current_condition += expr[i]
                i += 1

        if current_condition.strip():
            formatted_cond = "【" + current_condition.strip() + "】"
            tokens.append(formatted_cond)
        tokens = [t for t in tokens if t]
        print(f"DEBUG: Parsed tokens: {tokens}")
        if not tokens:
            return 0

        if tokens[0] in {'且', '或'}:
            error_detail = f"表达式格式错误：表达式不能以操作符开始。tokens={tokens}, expression={expression}"
            print(f"ERROR: {error_detail}")
            raise ValueError(error_detail)
        
        # 第一个必须是条件
        first_cond = tokens[0]
        result = (first_cond in satisfied_set)
        
        # 从左到右依次计算
        i = 1
        while i < len(tokens):
            if i + 1 >= len(tokens):
                error_detail = f"表达式格式错误：操作符后缺少条件。tokens={tokens}, expression={expression}, i={i}, len(tokens)={len(tokens)}"
                print(f"ERROR: {error_detail}")
                raise ValueError(error_detail)
            
            op = tokens[i]
            if op not in {'且', '或'}:
                error_detail = f"表达式格式错误：期望操作符'且'或'或'，但得到'{op}'。tokens={tokens}, expression={expression}, i={i}"
                print(f"ERROR: {error_detail}")
                raise ValueError(error_detail)
            
            next_cond = tokens[i + 1]
            if next_cond in {'且', '或'}:
                error_detail = f"表达式格式错误：期望条件，但得到操作符'{next_cond}'。tokens={tokens}, expression={expression}, i={i}"
                print(f"ERROR: {error_detail}")
                raise ValueError(error_detail)
            
            next_value = (next_cond in satisfied_set)
            if op == '且':
                result = result and next_value
            elif op == '或':
                result = result or next_value
            i += 2
        return 1 if result else 0

if __name__ == "__main__":
    true_conditions = ["【A】", "【B】", "【C】"]
    expression = "【A】且【B】或【C】"
    true_conditions = ["【组装前有小部件，且年龄：3岁以下】", "【有尖点利边且年龄：0-8岁）】"]
    expression = "【Toys Intended to be assembled by an adult】且【组装前有小部件，且年龄：3岁以下】或【有尖点利边且年龄：0-8岁）】"
    result = ConditionDecider.check_condition_expression(true_conditions, expression)
    print(result)
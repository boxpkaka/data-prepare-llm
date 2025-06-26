import json
import re

# 检测label里是否有非法的标点，中文

def check_punctuation(text):
    # 定义允许的标点符号：，。！？
    allowed_punctuation = {'，', '。', '！', '？'}
    # 使用正则表达式匹配所有标点符号
    punctuation_pattern = re.compile(r'[^\w\s]')  # 匹配非字母、数字、下划线、空格的字符
    # 找到所有标点符号
    found_punctuation = set(punctuation_pattern.findall(text))
    # print(f"{text} {found_punctuation}")
    # 检查是否包含非允许的标点符号
    return found_punctuation.issubset(allowed_punctuation)

def process_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        for line in file:
            line = line.strip()
            if not line:
                continue  # 跳过空行
            try:
                data = json.loads(line)
                text = data.get('text', '')  # 获取text字段，默认为空字符串
                if not check_punctuation(text):
                    print(f"包含其他标点符号的句子: {text}")
            except json.JSONDecodeError as e:
                print(f"JSON解析错误: {e}")
                continue

# 使用示例
file_path = '/workspace/volume/data-skh/luoyuanming/data/baidu_batch_api/zh_aishell4_norm_20250623_2/concat/head5000.jsonl'  # 替换为你的文件路径
process_file(file_path)
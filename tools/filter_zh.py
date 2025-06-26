import sys
from collections import Counter
import re

# 统计字的使用频率做出词表，挑出使用频率最高的前5000个字，然后清洗语料（句子中的字超过20%不在词表里就过滤）


def process_file(input_file, output_file, vocab_file, vocab_size=5000, threshold=0.2):
    # 第一步：读取文件并统计汉字频率
    hanzi_counter = Counter()
    lines = []
    
    with open(input_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
                
            # 分割ID和文本
            try:
                id, text, *_ = re.split(r"\s+", line.strip(), maxsplit=1)
            except ValueError as e:
                print(f"Line parse error: {line.strip()} - {e}")
                continue
            lines.append((id, text))
            
            # 统计汉字频率（只统计中文字符）
            for char in text:
                if '\u4e00' <= char <= '\u9fff':  # 判断是否为汉字
                    hanzi_counter[char] += 1
    
    # 第二步：生成词表文件（前5000个高频汉字）
    top_hanzi = hanzi_counter.most_common(vocab_size)
    vocab = set(char for char, count in top_hanzi)
    
    with open(vocab_file, 'w', encoding='utf-8') as f:
        for char, count in top_hanzi:
            f.write(f"{char} {count}\n")
    
    # 第三步：过滤文本行（超过20%汉字不在词表中的行被过滤）
    filtered_lines = []
    for id, text in lines:
        total_hanzi = 0
        missing_hanzi = 0
        
        for char in text:
            if '\u4e00' <= char <= '\u9fff':
                total_hanzi += 1
                if char not in vocab:
                    missing_hanzi += 1
        
        # 计算缺失比例（至少要有1个汉字才计算比例）
        if total_hanzi > 0 and (missing_hanzi / total_hanzi) <= threshold:
            filtered_lines.append(f"{id} {text}")
        else:
            print(f"过滤：${id} ${text}")
    
    # 第四步：保存过滤后的文件
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("\n".join(filtered_lines))

if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("用法: python script.py 输入文件 输出文件 词表文件")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2]
    vocab_file = sys.argv[3]
    
    process_file(input_file, output_file, vocab_file)
    print(f"处理完成！词表已保存到 {vocab_file}，过滤后的文本已保存到 {output_file}")
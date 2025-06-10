import json
import re
from pathlib import Path
from loguru import logger
import sys

# 配置日志
logger.remove()
logger.add(sys.stderr, level="INFO")
logger.add("check_zh_en_translate_result_filter_log.log", rotation="10 MB", level="DEBUG")

def is_valid_english(text):
    """严格检查英文：不能包含换行符或中文字符"""
    # 检查是否包含换行符
    if '\n' in text or '\r' in text:
        return False
    # 检查是否包含中文字符
    if re.search(r'[\u4e00-\u9fff]', text):
        return False
    return True

def process_line(line, line_num):
    try:
        data = json.loads(line.strip())
        if not all(key in data for key in ["zh-cn", "en", "wav_path"]):
            logger.warning(f"Line {line_num}: Missing required fields")
            return None
        
        # 严格校验英文
        if not is_valid_english(data["en"]):
            logger.warning(f"Line {line_num}: Invalid English text (contains newline/Chinese) - {data['en']}")
            return None
        
        # 检查wav_path是否非空
        if not data["wav_path"].strip():
            logger.warning(f"Line {line_num}: Empty wav_path")
            return None
        
        return data
    
    except json.JSONDecodeError:
        logger.error(f"Line {line_num}: Invalid JSON format")
        return None
    except Exception as e:
        logger.error(f"Line {line_num}: Unexpected error - {str(e)}")
        return None

def process_file(input_file, output_file):
    valid_count = 0
    invalid_count = 0
    
    with open(input_file, 'r', encoding='utf-8') as infile, \
         open(output_file, 'w', encoding='utf-8') as outfile:
        
        for line_num, line in enumerate(infile, 1):
            processed = process_line(line, line_num)
            if processed:
                json.dump(processed, outfile, ensure_ascii=False)
                outfile.write('\n')
                valid_count += 1
            else:
                invalid_count += 1
            
            # 每处理10万行输出一次进度
            if line_num % 100000 == 0:
                logger.info(f"Processed {line_num} lines (Valid: {valid_count}, Invalid: {invalid_count})")
    
    logger.info(f"Processing complete. Total: {line_num}, Valid: {valid_count}, Invalid: {invalid_count}")

if __name__ == "__main__":
    input_file = Path("/workspace/volume/data-skh/luoyuanming/data/baidu_batch_api/mt_trans_zh_250604/concat/mt_trans_zh_250604.jsonl")  # 输入文件路径
    output_file = Path("/workspace/volume/data-skh/luoyuanming/data/baidu_batch_api/mt_trans_zh_250604/concat/mt_trans_zh_250604_filtered.jsonl")  # 输出文件路径
    
    if not input_file.exists():
        logger.error(f"Input file not found: {input_file}")
        sys.exit(1)
    
    logger.info(f"Starting processing of {input_file}")
    process_file(input_file, output_file)
    logger.info(f"Filtered data saved to {output_file}")
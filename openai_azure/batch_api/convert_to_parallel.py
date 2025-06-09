import os
import re
from typing import Dict
import argparse
import pandas as pd
import ujson
from loguru import logger
from concurrent.futures import  as_completed, ProcessPoolExecutor
from multiprocessing import cpu_count
from datetime import datetime, timezone, timedelta
from time import sleep
import uuid

from utils.io import check_json_files_exist, write_json_file


ISO = {
    "Chinese": "zh-cn",
    "English": "en",
    "Spanish": "es",
    "Japanese": "ja",
    "Korean": "ko",
    "Thai": "th",
    "Arabic": "ar",
    "German": "de",
    "French": "fr",
    "Italian": "it",
    "Russian": "ru",
    "Portuguese": "pt",
    "Indonesian": "id",
    "Hindi": "hi",
    "Telugu": "te",
    "Tamil": "ta",
    "Urdu": "ur",
    "Vietnamese": "vi",
    "Malay": "ms",
    "Norwegian": "no",
    "Swedish": "sv",
    "Finnish": "fi",
    "Danish": "da",
    "Dutch": "nl",
    "Catalan": "ca",
    "Hebrew": "he",
    "Greek": "el",
    "Hungarian": "hu",
    "Polish": "pl",
    "Czech": "cs",
    "Slovak": "sk",
    "Romanian": "ro",
    "Slovenian": "sl",
    "Croatian": "hr",
    "Bulgarian": "bg",
    "Turkish": "tr",
    "Ukrainian": "uk",
    "Icelandic": "is",
    "Filipino": "fil",
    "Swahili": "sw",
    "Mongolian": "mn",
    "Persian": "fa",
    "Kazakh": "kk",
    "Uzbek": "uz",
    "Style": "style",
    "Scene": "scene"
}


DATA = {"结束时间": [],
        "文件名": [],
        "总行数": [],
        "总消耗token数": [],
        "发送token数": [],
        "返回token数": [],
        "发送总字符数": [],
        "返回总字符数": [],
        "平均每行消耗token数": [],
        "返回/发送token比": [],
        "token/字符比": []
        }

DATASET = "c4_en"

PATTERN_1 = re.compile(r'\*\*(.*?):\*\*')
PATTERN_2 = re.compile(r'[*>/"\'\\\.\[\]\(\)|:_;&😌😀-🙏🌀-🗿🚀-🛴🥇-🧿🧸-🧼🪀-🪙🪨-🪶🫀-🫓🫠-🫰🫳-🫶🫷-🫺🫻-🫾→←↑↓↔↕↖↗↘↙]|[^a-zA-Z0-9,\s]')


def timestamp_to_cntime(timestamp: int) -> str:
    utc_time = datetime.fromtimestamp(timestamp, tz=timezone.utc)
    cn_timezone = timezone(timedelta(hours=8))
    cn_time = utc_time.astimezone(cn_timezone).strftime('%Y-%m-%d %H:%M:%S')
    return cn_time
    
    
def get_statistic_data(converted_id_file: str) -> None:
    with open(converted_id_file, 'r', encoding='utf-8') as f:
        all_dict = ujson.load(f)
    
    for file_name, item in all_dict.items():
        timestamp = item.get('completed_at')
        if not timestamp:
            continue
        cn_time = timestamp_to_cntime(timestamp)
        
        lines = int(item['lines'])
        send_tokens = int(item['send_tokens'])
        receive_tokens = int(item['receive_tokens'])
        receive_chars = int(item['receive_chars'])
        send_chars = int(item['send_chars'])
        total_tokens = int(item['total_tokens'])
        
        per_line_tokens = total_tokens / lines
        receive_send_tokens_ratio = receive_tokens / send_tokens
        tokens_chars_ratio = total_tokens / (receive_chars + send_tokens)
        
        DATA["文件名"].append(file_name)
        DATA["结束时间"].append(cn_time)
        DATA["总行数"].append(lines)
        DATA["总消耗token数"].append(total_tokens)
        DATA["发送token数"].append(send_tokens)
        DATA["返回token数"].append(receive_tokens)
        DATA["发送总字符数"].append(send_chars)
        DATA["返回总字符数"].append(receive_chars)
        DATA["平均每行消耗token数"].append(per_line_tokens)
        DATA["返回/发送token比"].append(receive_send_tokens_ratio)
        DATA["token/字符比"].append(tokens_chars_ratio)
    
    # 将数据转换为DataFrame
    df = pd.DataFrame(DATA)
    
    # 按结束时间排序
    df['结束时间'] = pd.to_datetime(df['结束时间'])  # 转换为datetime类型
    df = df.sort_values(by='结束时间')  # 按结束时间升序排序

    # 保存到Excel文件
    output_file = "statistic.xlsx"
    df.to_excel(output_file, index=False)


def response_to_dict(response: str) -> Dict[str, str]:
    response = PATTERN_1.sub(r'\1:', response)
    dump_item = {}
    current_language = None
    current_text = ''

    for line in response.splitlines():
        splited_line = line.split(':', 1)
        if len(splited_line) == 2:
            lang = splited_line[0].strip()
            if lang in ISO:
                if current_language:
                    dump_item[ISO[current_language]] = current_text.strip()
                current_language = lang
                current_text = splited_line[1]
            else:
                current_text += f'\n{line}'
        else:
            current_text += f'\n{line}'
    
    if not current_language:
        return {}
    
    for special_key in ("style", "scene"):
        if dump_item.get(special_key):
            item = dump_item[special_key].split('\n', 1)[0]
            dump_item[special_key] = PATTERN_2.sub('', item).strip().lower()
    
    dump_item[ISO[current_language]] = current_text.strip()
    return dump_item


def process_file(name: str, in_dir: str, out_dir: str) -> dict | None:
    path_in = os.path.join(in_dir, name)
    if not os.path.exists(path_in):
        return None
    path_out = os.path.join(out_dir, name)
    statistic_item = {}
    statistic_item["send_tokens"] = 0
    statistic_item["receive_tokens"] = 0
    statistic_item["total_tokens"] = 0
    statistic_item["send_chars"] = 0
    statistic_item["receive_chars"] = 0
    statistic_item["lines"] = 0
    
    try:
        with open(path_in, 'r', encoding='utf-8', errors='ignore') as fin, \
            open(path_out, 'w', encoding='utf-8') as fout:
            for line in fin:
                try:
                    item = ujson.loads(line)
                except ujson.JSONDecodeError:
                    continue
                response = item['response']['body']['choices'][0]['message'].get('content', '')
                if not response:
                    continue
                custom_id = item["custom_id"]
                final_item = response_to_dict(response)
                if final_item:
                    final_item['dataset'] = DATASET
                    final_item["uuid"] = str(uuid.uuid4())
                    final_item['metadata'] = custom_id
                    ujson.dump(final_item, fout, ensure_ascii=False)
                    fout.write('\n')
                
                statistic_item["send_tokens"] += int(item['response']['body']['usage']["prompt_tokens"])
                statistic_item["receive_tokens"] += int(item['response']['body']['usage']["completion_tokens"])
                statistic_item["total_tokens"] += int(item['response']['body']['usage']["total_tokens"])
                statistic_item["receive_chars"] += len(response)
                statistic_item["send_chars"] += len(final_item.get('en', ''))
                statistic_item["lines"] += 1
                
        logger.success(f"{name} is processed. ")
        result = {
            name: statistic_item
        }
        return result
    except Exception as e:
        logger.error(f"{name} - {e}")
        return None


def process_single_config(root_dir: str) -> None:
    in_dir = os.path.join(root_dir, "gpt")
    out_dir = os.path.join(root_dir, "parallel")
    
    logger.info(f"Processing directory: {root_dir}")
    
    # create save directory and record file
    os.makedirs(out_dir, exist_ok=True)
    completions = os.path.join(out_dir, 'completions.json')
    check_json_files_exist(completions)
    
    with open(completions, 'r', encoding='utf-8') as f_completed:
        completed_items = ujson.load(f_completed)
    
    # get unprocessed file name list
    all_file_names = os.listdir(in_dir)
    completed_file_names = [k for k in completed_items]
    unprocess_file_names = set(all_file_names) - set(completed_file_names)
    
    # multi-thread executor
    with ProcessPoolExecutor(max_workers=cpu_count()) as executor:
        futures = [
            executor.submit(process_file, name, in_dir, out_dir) for name in unprocess_file_names
        ]
    
    # collect results
    record_items = []
    for future in as_completed(futures):
        try:
            result = future.result()  # 获取返回值
            if result:
                record_items.append(result)
        except Exception as e:
            logger.error(f"Error processing file: {e}")
    
    # record results
    for record_item in record_items:
        file_name = list(record_item.keys())[0]
        infos = record_item.get(file_name)
        write_json_file(path=completions, key=file_name, value=infos)
    
    logger.success("Processing is done. ")
        

def main(args):
    with open(args.config_path, 'r', encoding='utf-8') as f:
        config = ujson.load(f)
    
    wait_time = 1800
    while True:
        for config_name, single_config in config.items():
            logger.info(f"Processing: {config_name}")
            root_dir = single_config.get("data_dir")
            process_single_config(root_dir=root_dir)
        
        logger.info(f"waiting {wait_time}s. ")
        sleep(wait_time)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config_path",     help="", type=str)
    args = parser.parse_args()

    main(args)

    
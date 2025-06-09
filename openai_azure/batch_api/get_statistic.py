import argparse
import os
from datetime import datetime, timedelta, timezone

import pandas as pd
import ujson
from loguru import logger
from pathlib import Path

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
        "token/字符比": [],
        "资源名": []
        }


def timestamp_to_cntime(timestamp: int) -> str:
    utc_time = datetime.fromtimestamp(timestamp, tz=timezone.utc)
    cn_timezone = timezone(timedelta(hours=8))
    cn_time = utc_time.astimezone(cn_timezone).strftime('%Y-%m-%d %H:%M:%S')
    return cn_time

def time_str_to_timestamp(time_str: str) -> int:
    time_obj = datetime.strptime(time_str, "%Y-%m-%d %H-%M-%S")
    timestamp = time_obj.timestamp()
    return timestamp

def process_dir(config: dict, config_name: str) -> None:
    data_dir = config.get("data_dir")
    id_file = config.get("id_file")
    parallel_dir = os.path.join(data_dir, "parallel")
    completions = os.path.join(parallel_dir, 'completions.json')
    
    with open(id_file, 'r', encoding='utf-8') as f:
        id_file_items = ujson.load(f)
    
    with open(completions, 'r', encoding='utf-8') as f:
        completions = ujson.load(f)
        
    for file_name, item in completions.items():
        try:
            timestamp = id_file_items.get(file_name, {}).get('completed_at', 0)
            if not timestamp:
                timestamp = 0
                # time_str = id_file_items.get("metadata").get("time")
                # timestamp = time_str_to_timestamp(time_str)
            
            cn_time = timestamp_to_cntime(timestamp)

            lines = int(completions[file_name]["lines"])
            send_tokens = int(completions[file_name]['send_tokens'])
            receive_tokens = int(completions[file_name]['receive_tokens'])
            receive_chars = int(completions[file_name]['receive_chars'])
            send_chars = int(completions[file_name]['send_chars'])
            total_tokens = int(completions[file_name]['total_tokens'])
            
            if lines == 0:
                lines = 1
            
            if send_tokens == 0:
                send_tokens = 1
            
            per_line_tokens = total_tokens / lines
            receive_send_tokens_ratio = receive_tokens / send_tokens
            tokens_chars_ratio = total_tokens / (receive_chars + send_tokens)
            
            DATA["文件名"].append(file_name)
            DATA["结束时间"].append(str(cn_time))
            DATA["总行数"].append(lines)
            DATA["总消耗token数"].append(total_tokens)
            DATA["发送token数"].append(send_tokens)
            DATA["返回token数"].append(receive_tokens)
            DATA["发送总字符数"].append(send_chars)
            DATA["返回总字符数"].append(receive_chars)
            DATA["平均每行消耗token数"].append(per_line_tokens)
            DATA["返回/发送token比"].append(receive_send_tokens_ratio)
            DATA["token/字符比"].append(tokens_chars_ratio)
            DATA["资源名"].append(config_name)
            
        except KeyError as e:
            logger.info(f"KeyError:{e} skipped, config_name: {config_name}")
            continue
        
        except ZeroDivisionError:
            logger.info(f"lines=0, skip {file_name}")


def main(args) -> None:
    config_path = Path(args.config_path)
    
    with open(config_path, 'r', encoding='utf-8') as f_config:
        config_all = ujson.load(f_config)
    
    for config_name, config in config_all.items():
        process_dir(config=config, config_name=config_name)
    
        # 将数据转换为DataFrame
    df = pd.DataFrame(DATA)

    # 按结束时间排序
    df['结束时间'] = pd.to_datetime(df['结束时间'])  # 转换为datetime类型
    df = df.sort_values(by='结束时间')  # 按结束时间升序排序

    # 保存到Excel文件
    output_file = Path("statistic") / f"{config_path.stem}.xlsx"
    df.to_excel(output_file, index=False)
    logger.success("Processing is done. ")
    
    
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config_path", help="", type=str)
    args = parser.parse_args()
    
    main(args)

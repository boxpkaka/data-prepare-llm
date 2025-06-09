from datetime import datetime
import pandas as pd
import os
import re


DATE_FORMAT = "%Y-%m-%d %H:%M:%S.%f"
PATH_PATTERN = re.compile(r'([^/]+\.json)')
LINES_PATTERN = re.compile(r'Processed (\d+)/')
TOKEN_PATTERN = re.compile(r'Total prompt tokens:\s(\d+)')
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

def read_last_two_lines(file_path: str) -> tuple:
    with open(file_path, 'rb') as file:
        file.seek(0, 2)  # 移动到文件末尾
        position = file.tell()
        line1 = b''
        line2 = b''
        buffer = b''

        while position >= 0:
            file.seek(position)
            char = file.read(1)
            if char == b'\n':
                if line1:
                    line2 = line1
                    line1 = buffer
                    buffer = b''
                elif buffer:
                    line1 = buffer
                    buffer = b''
                if line1 and line2:
                    break
            buffer = char + buffer
            position -= 1

        return (line1.decode('utf-8'), line2.decode('utf-8'))

if __name__ == "__main__":
    log_dir = '/home/mingdongyu/workspace/data_prepare_gpt/log/norm_log'
    log_paths = [os.path.join(log_dir, x) for x in os.listdir(log_dir)]
    
    meta_data = []
    for log_path in log_paths:
        second_last_line, last_line = read_last_two_lines(log_path)
        all_lines = LINES_PATTERN.search(second_last_line)
        if all_lines is None:
            continue
        all_lines = all_lines.group(1)
        splited_line = [x.strip() for x in last_line.split('|')]
        splited_line = [x for x in splited_line if x]
        splited_line.append(all_lines)
        if splited_line[1].strip() == 'SUCCESS':
            meta_data.append(splited_line)

    meta_data = sorted(meta_data, key=lambda x: datetime.strptime(x[0], DATE_FORMAT), reverse=False)
    for data in meta_data:
        end_time = data[0]
        file_name = PATH_PATTERN.search(data[2]).group(1)
        send_tokens = int(TOKEN_PATTERN.search(data[2]).group(1))
        all_lines = int(data[-1])
        total_tokens = int(data[4].split(': ')[-1])
        receive_tokens = int(data[3].split(': ')[-1])
        send_chars = int(data[5].split(': ')[-1])
        receive_chars = int(data[6].split(': ')[-1])
        DATA['结束时间'].append(end_time)
        DATA["文件名"].append(str(file_name))
        DATA["总行数"].append(str(all_lines))
        DATA["总消耗token数"].append(str(total_tokens))
        DATA['发送token数'].append(str(send_tokens))
        DATA["返回token数"].append(str(receive_tokens))
        DATA["发送总字符数"].append(str(send_chars))
        DATA["返回总字符数"].append(str(receive_chars))
        DATA["平均每行消耗token数"].append(f"{total_tokens/all_lines:.1f}")
        DATA["返回/发送token比"].append(f"{receive_tokens/send_tokens:.1f}")
        DATA["token/字符比"].append(f"{total_tokens/(send_chars+receive_chars):.1f}")
            
    df = pd.DataFrame(DATA)
    output_file = "statistic.xlsx"
    df.to_excel(output_file, index=False)
    
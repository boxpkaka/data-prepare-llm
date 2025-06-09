import os
import json
import string
import multiprocessing
from loguru import logger
from langdetect import detect
from datetime import datetime

STRING_FLAG = {'中文：', '英文：', '西班牙文：', '日文：', '韩文：', '泰文：', '阿拉伯文：','中(简体)：',
                '- 中文：', '- 英文：', '- 西班牙文：', '- 日文：', '- 韩文：', '- 泰文：', '- 阿拉伯文：',
                '中文:', '英文:', '西班牙文:', '日文:', '韩文:', '泰文:', '阿拉伯文:',
                '西班牙语：', '日语：', '韩语：', '英语：', '泰语：', '阿拉伯语：',
                '西班牙语:', '日语:', '韩语:', '英语:', '泰语:', '阿拉伯语:',
                'Chinese (中文):', 'English:', 'Spanish (Español):', 'Japanese (日本語):',
                'Korean (한국어):', 'Thai (ไทย):', 'Arabic (ﺎﻠﻋﺮﺒﻳﺓ):',
                'Chinese:', 'English:', 'Spanish:', 'Japanese:', 'Korean:', 'Arabic:', 'Thai:',
                'Chinese (Simplified):','Español (Spanish):', '日本語 (Japanese):', '한국어 (Korean):', 'ไทย (Thai):'
                'ﺎﻠﻋﺮﺒﻳﺓ (Arabic):'}

def find_multi_files(root_dir):
    multi_files = {}
    for dirpath, dirnames, filenames in os.walk(root_dir):
        for filename in filenames:
            if filename.endswith('.multi'):
                if filename not in multi_files:
                    multi_files[filename] = os.path.join(dirpath, filename)
    return list(multi_files.values())

def detect_language(text):
    try:
        return detect(text)
    except:
        return 'unknown'

def remove_flag(text):
    for flag in STRING_FLAG:
        if text.startswith(flag):
            return text[len(flag):].strip()
    return text.strip()

def unzip_corpurs(args):
    in_file, out_dir = args
    clean_cnt = 0
    dirty_cnt = 0
    
    file_name = in_file.split('/')[-1]
    logger_file = f'{os.path.join(out_dir, file_name)}.log'
    out_file = f'{os.path.join(out_dir, file_name)}.json'
    
    logger.add(logger_file, level="DEBUG", rotation="10 MB",  filter=lambda x: f'[{file_name}]' in x['message'])
    logger.info(f"[{file_name}] processing file: {file_name}")

    with open(in_file, 'r', encoding='utf-8') as f_in, open(out_file, 'w', encoding='utf-8') as f_out:
        all_list = f_in.readlines()
        all_text = ''.join(all_list)
        splited_text = all_text.split('test48:')
        for line in splited_text:
            if line:
                _splited = line.split('\n')
                if len(_splited) < 7:
                    dirty_cnt += 1
                    continue
                _clean = []
                for i in _splited:
                    if i in STRING_FLAG or i == '' \
                        or '平行语料' in i \
                        or 'ai language model' in i.lower() \
                        or 'parallel corpus' in i.lower() \
                        or all(char in string.punctuation for char in i):
                        continue
                    if '请注意' in i or '很抱歉' in i:
                        break
                    _clean.append(i)
                    
                if len(_clean) == 0:
                    continue
                # 首句如果是英文直接去掉
                while(_clean):
                    if detect_language(_clean[0]) == 'zh-cn':
                        break
                    _clean = _clean[1:]
                
                # 语种少于5种扔掉
                lang_set = set()
                for line in _clean:
                    lang_set.add(detect_language(line))
                    
                if len(lang_set)  < 4:
                    dirty_cnt += 1
                    filtered_response = '|'.join(_clean)
                    logger.warning(f'[{file_name}] [reject] - {filtered_response} [accept: {clean_cnt} reject: {dirty_cnt}]')
                else:
                    item = {
                        'zh-cn': '', 
                        'en': '', 
                        'es': '', 
                        'ja': '', 
                        'ko': '', 
                        'th': '', 
                        'ar': '',
                        'de': '',
                        'fr': '',
                        'it': '',
                        'ru': '',
                    }
                    for line in _clean:
                        line = remove_flag(line)
                        _lang = detect_language(line)
                        if _lang in item:
                            item[_lang] = ''.join([item[_lang], line])
                        else:
                            logger.warning(f'[{file_name}] [Wrong language]: {_lang} - {line}')
                    clean_cnt += 1
                    json.dump(item, f_out, ensure_ascii=False)
                    f_out.write('\n')
                        
    logger.success(f'[{file_name}] {in_file}: [accept: {clean_cnt} reject: {dirty_cnt}]')
    
def get_json_from_zhenhui_data(root_dir: str, out_dir: str):
    date_now = datetime.now().strftime("%Y-%m-%d-%H:%M")    
    global_log_path = os.path.join(out_dir, f'{date_now}.global.log')
    
    logger.add(global_log_path, level="DEBUG", rotation="100 MB", filter=lambda x: '[global]' in x['message'])
    file_paths = find_multi_files(root_dir)
    
    with multiprocessing.Pool(processes=32) as pool:
        pool.map(unzip_corpurs, [(file_path, out_dir) for file_path in file_paths])

if __name__ == "__main__":
    root_dir='/nasStore/zhenhui_zh_data/gpt/'
    out_dir='/nasStore/mingdong_data/zhenhui_data'
    get_json_from_zhenhui_data(root_dir, out_dir)

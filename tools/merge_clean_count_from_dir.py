import os
import re
import sys
import ujson
from tqdm import tqdm
from multiprocessing import Process, Manager, Queue

# Initialize constants and patterns
BEGIN_FLAG = [
    '中文', '英文', '西班牙文', '日文', '韩文', '泰文', '阿拉伯文', '中(简体)',
    '西班牙语', '西语', '日语', '韩语', '英语', '泰语', '阿拉伯语',
    'Chinese', 'English', 'Spanish', 'Japanese', 'Korean', 'Arabic', 'Thai',
    'Chinese (中文)', 'Spanish (Español)', 'Japanese (日本語)',
    'Korean (한국어)', 'Thai (ไทย)', 'Arabic (ﺎﻠﻋﺮﺒﻳﺓ)',
    'Chinese (Simplified)', 'Español (Spanish)', '日本語 (Japanese)', '한국어 (Korean)', 'ไทย (Thai)',
    'ﺎﻠﻋﺮﺒﻳﺓ (Arabic)', 'translation:'
]
ALL_LANG = ['zh-cn', 'en', 'ja', 'ko', 'es', 'th', 'de', 'fr', 'it', 'ru', 'ar']
CLEAN_LANG = ['zh-cn', 'en', 'ja', 'ko', 'es', 'th', 'ru', 'ar']

BRACKETS_PATTERN = re.compile(r'\(.*?transla.*?\)', re.IGNORECASE)
IGNORE_PATTERN = re.compile(r'Provide the translation', re.IGNORECASE)
WEB_SITE_PATTERN = re.compile(r'https:\/\/[^\s]+')
END_LANGUAGE_PATTERN = re.compile(r'\((Chinese|English|Japanese|Korean|Spanish|Thai|German|French|Italian|Russian|Arabic)\)$')
ZH_PATTERN = re.compile(r'\(.*?翻译.*?\)', re.IGNORECASE)
ZH_PATTERN_2 = re.compile(r'(中：|中文：|- 中文：|中:|中文:|- 中文:)')
JA_PATTERN = re.compile(r'(日：|日文：|- 日文：|日:|日文:|- 日文:)|日语|日语:|日语：')
NO_ZH_PATTERN = re.compile(r'[\(\)（）\-：:\s]*[\u4e00-\u9fff]+[\(\)（）\-：:\s]*')
NO_TRANS_PATTERN = re.compile(r'[\x00-\x7F]*' + re.escape('translat') + r'[\x00-\x7F]*[.!?。！？]', re.IGNORECASE)

# Compile regex for BEGIN_FLAG and characters to remove
BEGIN_FLAG_PATTERN = re.compile(r'|'.join(re.escape(flag) for flag in sorted(BEGIN_FLAG, key=len, reverse=True)))
CHARACTER_PATTERN = re.compile(r'^[）:)\.：\-]+')

def clean_text(text: str, lang: str) -> str:
    if IGNORE_PATTERN.search(text) or not text:
        return ''
    text = BRACKETS_PATTERN.sub('', text)
    text = WEB_SITE_PATTERN.sub('', text)
    if lang == 'zh-cn':
        text = ZH_PATTERN.sub('', text)
        text = ZH_PATTERN_2.sub('', text)
    if lang == 'ja':
        text = JA_PATTERN.sub('', text)
    if lang != 'zh-cn' and lang != 'ja':
        text = NO_ZH_PATTERN.sub('', text)
    if lang != 'en':
        text = NO_TRANS_PATTERN.sub('', text)
    
    text = BEGIN_FLAG_PATTERN.sub('', text)
    text = text.strip()
    text = CHARACTER_PATTERN.sub('', text)
    text = END_LANGUAGE_PATTERN.sub('', text)
    
    return text.strip()

def process_file(path, counts, output_queue):
    buffer = []
    try:
        with open(path, 'r', encoding='utf-8', errors='ignore') as fin:
            for line in fin:
                try:
                    items = ujson.loads(line)
                except Exception:
                    continue
                for lang in ALL_LANG:
                    text = items.get(lang, '')
                    if not text:
                        items[lang] = ''
                        continue
                    if lang in CLEAN_LANG:
                        items[lang] = clean_text(text, lang)
                        counts[lang] += 1
                    else:
                        counts[lang] += 1
                buffer.append(ujson.dumps(items, ensure_ascii=False) + '\n')
                
    except Exception as e:
        print(f"Error processing file {path}: {e}")
    output_queue.put(buffer)

def writer_process(save_path, output_queue, total_files):
    with open(save_path, 'w', encoding='utf-8') as fout:
        for _ in tqdm(range(total_files), total=total_files):
            buffer = output_queue.get()
            fout.writelines(buffer)

def main(jsons_dir:str, save_path: str):
    json_paths = [os.path.join(jsons_dir, x) for x in os.listdir(jsons_dir) if x.endswith('json')]
    
    manager = Manager()
    counts = manager.dict({x: 0 for x in ALL_LANG})
    output_queue = Queue()

    writer = Process(target=writer_process, args=(save_path, output_queue, len(json_paths)))
    writer.start()

    processes = []
    for path in json_paths:
        p = Process(target=process_file, args=(path, counts, output_queue))
        p.start()
        processes.append(p)

    for p in processes:
        p.join()

    output_queue.put(None)  # Signal the writer to stop
    writer.join()

    with open(save_path + '.num', 'w', encoding='utf-8') as f_num:
        ujson.dump(dict(counts), f_num, ensure_ascii=False)

if __name__ == "__main__":
    jsons_dir = '/nasStore/mingdong_data/supplement_zhenhui_data' 
    save_path = sys.argv[1]
    main(jsons_dir, save_path)
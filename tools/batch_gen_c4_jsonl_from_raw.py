from multiprocessing import Pool, cpu_count
from typing import List
from tqdm import tqdm
import ujson
import sys
import re
import os

NEED_LANG = ["Chinese", "Spanish", "Japanese", "Korean", "Thai", 
             "Arabic","German", "French", "Italian", "Russian"]
LIMIT_CHAR = 400
LIMIT_REQUEST = 50000
MAX_FILE_SIZE = 99 * 1024 * 1024
MAX_TOKENS = 10000

SPLIT_PATTERN = re.compile(r'(?<=[.!?\n]) +')
PROMPT_PREFIX = "Translate the following English sentence into the specified languages. Provide the translations in the format below. Include the original text and translations only, without any additional content."
PROMPT_SUFFIX = ': \n'.join(NEED_LANG)

def get_prompted_text(text_in: str) -> str:
    text_out = f"{PROMPT_PREFIX}\n\nEnglish: {text_in}\n{PROMPT_SUFFIX}"
    return text_out

def split_text(text: str) -> List[str]:
    paragraphs = text.strip().split('\n')
    result = []
    for paragraph in paragraphs:
        sentences = SPLIT_PATTERN.split(paragraph.strip())
        current_chunk = ""
        
        for sentence in sentences:
            sentence = sentence.strip()
            if len(current_chunk) + len(sentence) + 1 <= LIMIT_CHAR:
                current_chunk += (sentence + " ")
            else:
                result.append(current_chunk.strip())
                current_chunk = sentence + " "
        
        if current_chunk:
            result.append(current_chunk.strip())
    
    return result

def process_file(file_name: str, root_dir: str, output_dir: str, completion_file_path: str):
    index = 0
    cnt = 0
    path_in = os.path.join(root_dir, file_name)
    
    fout = open(f'{os.path.join(output_dir, file_name)}-{index}.jsonl', 'w', encoding='utf-8')
    with open(path_in, 'r', encoding='utf-8') as fin:
        for line in fin:
            text = ujson.loads(line)["text"]
            sentences = split_text(text)
            for sentence in sentences:
                prompt = get_prompted_text(sentence)
                messages = [
                    {
                        "role": "system",
                        "content": prompt
                    }
                ]
                dump_item = {
                    "custom_id":f'{file_name}-{index}-{cnt}',
                    "method": "POST",
                    "url": "/v1/chat/completions",
                    "body": {
                        "model": "gpt-4o-mini",
                        "messages": messages,
                        "max_tokens": 10000
                        },
                }
                ujson.dump(dump_item, fout, ensure_ascii=False)
                fout.write('\n')
                cnt += 1
                if os.fstat(fout.fileno()).st_size >= MAX_FILE_SIZE or cnt == LIMIT_REQUEST-1:
                    index += 1
                    cnt = 0
                    fout.close()
                    fout = open(f'{os.path.join(output_dir, file_name)}-{index}.jsonl', 'w', encoding='utf-8')
    fout.close()
    
    # 标记文件已处理完毕
    with open(completion_file_path, 'a', encoding='utf-8') as f_check:
        f_check.write(os.path.basename(path_in) + '\n')

def main(root_dir: str, output_dir: str):
    completion_file_path = os.path.join(output_dir, 'completion.txt')
    if not os.path.exists(completion_file_path):
        os.system(r"touch {}".format(completion_file_path))
        print(f"generate complete file: {completion_file_path}")
    
    # 读取已完成的文件
    completions = set()
    with open(completion_file_path, 'r', encoding='utf-8') as f_check:
        for file_name in f_check:
            completions.add(file_name.strip())

    process_file_names = set(os.listdir(root_dir)) - completions
    
    # 使用多进程处理文件
    with Pool(processes=cpu_count()) as pool:
        for file_name in tqdm(process_file_names):
            pool.apply_async(process_file, args=(file_name, root_dir, output_dir, completion_file_path))
        pool.close()
        pool.join()

if __name__ == "__main__":
    root_dir = "/workspace/volume/data3-lianxiang/300-MT-Pro/data/c4/en"
    output_dir = "/workspace/volume/data3-lianxiang/300-MT-Pro/data/c4/en_batch_api"
    main(root_dir, output_dir)
from get_openai_model_list import get_model_type_dict
from typing import Dict, Tuple, List
from queue import Queue
from time import sleep
from multiprocessing import Value
from loguru import logger
from datetime import datetime

import os
import openai
import json
import threading
import argparse
import queue


# API_KEY = "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"
# MAX_TOKEN = 2500
# NUM_THREADS = 128
# MODEL_NAME = 'gpt-3.5-turbo-0125'

ISO = {
    'zh-cn': "Chinese",
    'ja': "Japanese",
    'ko': "Korean",
    'en': "English",
    "es": "Spanish",
    "th": "Thai",
    "ar": "Arabic",
    "de": "German",
    "fr": "French",
    'it': "Italian",
    "ru": "Russian"
}

# def count_tokens(text, model="gpt-3.5-turbo"):
#     encoding = tiktoken.encoding_for_model(model)
#     tokens = encoding.encode(text)
#     return len(tokens)

def create_lock(lock_file: str):
    with open(lock_file, 'w') as lock:
        lock.write('locked')

def remove_lock(lock_file: str):
    os.remove(lock_file)

def get_supplement_prompt(ref_dict: Dict) -> Tuple[str, str]:
    need_lang = []
    for lang, text in ref_dict.items():
        if text == "":
            need_lang.append(ISO[lang])
    if len(need_lang) == 0:
        return
    ref_lang, ref_text = 'Chinese', ref_dict['zh-cn']
    if ref_dict['zh-cn'] == "":
        if ref_dict['en']:
            ref_lang, ref_text = 'English', ref_dict['en']
        else:
            for lang, text in ref_dict.items():
                if text:
                    ref_lang, ref_text = lang, text
    token_1 = f"{','.join(need_lang[:-1])} and {need_lang[-1]}"
    token_2 = f"{ref_lang}: {ref_text}"
    token_3 = []
    for lang in need_lang:
        token_3.append(f'{lang}: Provide the translation here.')
    token_3 = '\n    '.join(token_3)
    prompt = f"""
    Translate the following {ref_lang} sentence into {token_1}. Provide the translation for each language in the following format:

    {token_2}
    {token_3}
    """
    return prompt, ref_text
    
def fetch_translation(client, ref_dict, output_queue, counter, total, token_counter, model_type, args):
    try:
        prompt, ref_text = get_supplement_prompt(ref_dict)
    except Exception as e:
        output_queue.put(ref_dict)
        return
    
    backoff_time = 0.3
    while True:
        try:
            if args.is_azure:
                response = client.chat.completions.create(
                    model=args.model_name, # model = "deployment_name".
                    messages=[
                        {"role": "system", "content": prompt},
                    ]
                )
                message = response.choices[0].message.content
                if not message:
                    logger.warning(f"Responsed nothing - {ref_text}")
                    output_queue.put(ref_dict)
                    return
                
                prompt_tokens = response.usage.prompt_tokens
                completion_tokens = response.usage.completion_tokens
                all_tokens = response.usage.total_tokens
                result = response_to_dict(ref_dict, message)
                num_prompt = len(prompt)
                num_response = len(message)
                output_queue.put(result)
                
            elif model_type == 'completions':
                response = client.completions.create(
                    model=args.model_name,
                    prompt=prompt,
                    max_tokens=args.max_token
                )
                output_queue.put(response.choices[0].text.strip())
            elif model_type == 'chat':
                response = client.chat.completions.create(
                    model=args.model_name,
                    messages=[{"role": "system", "content": prompt}],
                )
                output_queue.put(response.choices[0].message.content)
            else:
                logger.error(f"Unsupport model type for {args.model_name}: {model_type}")
                raise NotImplementedError
            break
        except openai.RateLimitError as e:
            logger.warning(f"Rate limit hit: {e}. Retrying in {backoff_time} seconds...")
            sleep(backoff_time)
            backoff_time *= 2
            if backoff_time > 10:
                output_queue.put(ref_dict)
                return
        except Exception as e:
            logger.error(f"Error fetching translation for {ref_text}: {e}")
            output_queue.put(ref_dict)
            return
    with counter.get_lock():
        counter.value += 1
        token_counter['prompt_tokens'].value += prompt_tokens
        token_counter['completion_tokens'].value += completion_tokens
        token_counter['total_tokens'].value += all_tokens
        token_counter['num_prompt'].value += num_prompt
        token_counter['num_response'].value += num_response
        if counter.value % 100 == 0 or counter.value == total:
            logger.info(f"[Logger] Processed {counter.value}/{total} lines.| " 
                        f"Total prompt tokens: {token_counter['prompt_tokens'].value} |" 
                        f"completion tokens: {token_counter['completion_tokens'].value} |" 
                        f"total tokens: {token_counter['total_tokens'].value} |"
                        f"num_prompt: {token_counter['num_prompt'].value} |"
                        f"num_response: {token_counter['num_response'].value} |")

def response_to_dict(ref_dict: Dict[str, str], response: str) -> Dict[str, str]:
    try:
        lines = response.strip().split('\n')
        for line in lines:
            parts = line.split(': ', 1)
            if len(parts) == 2:
                language, translation = parts
                language = language.strip()
                translation = translation.strip()
                for iso_code, lang in ISO.items():
                    if lang == language and iso_code in ref_dict and not ref_dict[iso_code]:
                        ref_dict[iso_code] = translation
                        break
    except Exception as e:
        logger.error(f"Error from response {response}: {e}")
        return ref_dict
    return ref_dict

def worker(input_queue, output_queue, counter, total, token_counter, model_type, args):
    if args.is_azure:
        client = openai.AzureOpenAI(
            azure_endpoint=args.azure_end_point,
            api_key=args.api_key,
            api_version=args.api_version,
        )
    else:
        client = openai.OpenAI(api_key=args.api_key)
    while True:
        line = input_queue.get()
        if line is None:
            input_queue.task_done()
            break
        fetch_translation(client, line, output_queue, counter, total, token_counter, model_type, args)
        input_queue.task_done()

def collect_data_from_gpt(args) -> None:
    input_queue = Queue()
    output_queue = Queue()
    logger.success("Client has been created!")
    logger.info(f"Model: {args.model_name}")
    
    model_type = ''
    if not args.is_azure:
        name_type_dict = get_model_type_dict()
        model_type = name_type_dict[args.model_name]
    
    # 按最后修改时间排序文件
    files_with_mtime = []
    for filename in os.listdir(args.data_dir):
        if filename.endswith('.json'):
            file_path = os.path.join(args.data_dir, filename)
            mtime = os.path.getmtime(file_path)
            files_with_mtime.append((file_path, mtime))

    files_with_mtime.sort(key=lambda x: x[1])
    
    completed_file = set()
    try:
        with open('completion.txt', 'r', encoding='utf-8') as f_check:
            for f_name in f_check:
                completed_file.add(f_name.strip())
    except Exception as e:
        logger.warning("Completion.txt doesn't exist.")
    
    all_logger_file = os.path.join('/home/mingdongyu/workspace/data_prepare_gpt/log', 
                            f'ALL-{args.model_name}-{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}.log')
    # 从最早的文件开始，如果已完成或正在被写入就跳过
    print(files_with_mtime)
    for file_name, mtime in files_with_mtime:        
        save_path = os.path.join(args.save_dir, os.path.basename(file_name))
        if save_path in completed_file:
            continue

        lock_file = save_path + '.lock'
        if os.path.exists(lock_file):
            logger.warning(f"{save_path} is writen by other, going to next file")
            continue
        
        # 独立logger文件
        model_name = args.model_name
        logger_file = os.path.join('/home/mingdongyu/workspace/data_prepare_gpt/log/norm_log', 
                                   f'{model_name}-{os.path.basename(file_name)}.log')
        
        logger.add(all_logger_file, level="DEBUG", rotation="500 MB")
        logger.add(logger_file, level="DEBUG", rotation="100 MB",  filter=lambda x: '[Logger]' in x['message'])
        
        create_lock(lock_file)
        logger.info(f"Start supplementary: {save_path}")

        refs = []
        with open(file_name, 'r+', encoding='utf-8') as fin:
            for line in fin:
                refs.append(json.loads(line))
        total = len(refs)
        for line in refs:
            input_queue.put(line)

        counter = Value('i', 0)
        token_counter = {
            'prompt_tokens': Value('i', 0),
            'completion_tokens': Value('i', 0),
            'total_tokens': Value('i', 0),
            'num_prompt': Value('i', 0),
            'num_response': Value('i', 0)
        }
        threads = []
        for _ in range(args.thread):
            t = threading.Thread(target=worker, args=(input_queue, output_queue, counter, total, token_counter, model_type, args))
            t.start()
            threads.append(t)
            
        logger.debug("Started all threads.")
        with open(save_path, 'w', encoding='utf-8') as fout:
            for _ in range(total):
                try:
                    result = output_queue.get(timeout=30)
                    if result:
                        json.dump(result, fout, ensure_ascii=False)
                        fout.write('\n')
                except queue.Empty:
                    logger.error("Output queue get operation timed out.")
                    break
                
        logger.debug("Processing completed. Sending stop signals to threads.")
        for _ in range(args.thread):
            input_queue.put(None)

        input_queue.join()
        
        logger.debug("Waiting for threads to finish.")
        for t in threads:
            t.join()
        
        logger.success(f"{save_path}")
        remove_lock(lock_file)
        with open('completion.txt', 'a', encoding='utf-8') as f:
            f.write(save_path + '\n')
        
        logger.success(f"[Logger] {save_path} is done!"
                        f"Total prompt tokens: {token_counter['prompt_tokens'].value} |" 
                        f"completion tokens: {token_counter['completion_tokens'].value} |" 
                        f"total tokens: {token_counter['total_tokens'].value} |"
                        f"num_prompt: {token_counter['num_prompt'].value} |"
                        f"num_response: {token_counter['num_response'].value} |")
        logger.remove()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='eval whisper')
    parser.add_argument('--api_key',                help='',                           type=str)
    parser.add_argument('--is_azure',               action='store_true')
    parser.add_argument('--api_version',            default='2024-04-01-preview',      type=str)
    parser.add_argument('--azure_end_point',        help='',                           type=str)
    parser.add_argument('--max_token',              help='',                           type=int)
    parser.add_argument('--thread',                 help='',                           type=int)
    parser.add_argument('--model_name',             help='',                           type=str)
    parser.add_argument('--data_dir',               help='',                           type=str)
    parser.add_argument('--save_dir',               help='',                           type=str)
    args = parser.parse_args()
    
    collect_data_from_gpt(args)

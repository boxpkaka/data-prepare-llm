from get_openai_model_list import get_model_type_dict

from queue import Queue
from time import sleep
from multiprocessing import Value
from loguru import logger
from typing import Tuple

import os
import openai
import sys
import threading
import argparse


# API_KEY = "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"
# MAX_TOKEN = 2500
# NUM_THREADS = 128
# MODEL_NAME = 'gpt-3.5-turbo-0125'
NEED_LANG = ['English']

def get_prompt(ref_zh) -> Tuple[str, str]:
    need_lang = []
    token_1 = f"{','.join(NEED_LANG[:-1])} and {NEED_LANG[-1]}"
    token_2 = f"Chinese: {ref_zh}"
    token_3 = []
    for lang in need_lang:
        token_3.append(f'{lang}: Provide the translation here.')
    token_3 = '\n    '.join(token_3)
    prompt = f"""
    Translate the following Chinese sentence into {token_1}. Provide the translation for each language in the following format:

    {token_2}
    {token_3}
    """
    return prompt

def fetch_translation(client, line, output_queue, counter, total, model_type, args):
    ref_zh = line.strip()
    prompt = get_prompt(ref_zh)
    
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
                output_queue.put(response.choices[0].message.content)
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
            logger.error(f"Rate limit hit: {e}. Retrying in {backoff_time} seconds...")
            sleep(backoff_time)
            backoff_time *= 2
            if backoff_time > 60:
                backoff_time = 60
        except Exception as e:
            logger.error(f"Error fetching translation for {ref_zh}: {e}")
            output_queue.put(None)
            break
    with counter.get_lock():
        counter.value += 1
        if counter.value % 100 == 0 or counter.value == total:
            logger.info(f"Processed {counter.value}/{total} lines.")


def worker(input_queue, output_queue, counter, total, model_type, args):
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
            break
        fetch_translation(client, line, output_queue, counter, total, model_type, args)
        input_queue.task_done()


def collect_data_from_gpt(args) -> None:
    input_queue = Queue()
    output_queue = Queue()
    save_path = os.path.join(args.save_dir, os.path.basename(args.data_path))
    logger.success("Client has been created!")
    logger.info(f"Model: {args.model_name}")
    logger.info(f"Save path: {save_path}")
    
    model_type = ''
    if not args.is_azure:
        name_type_dict = get_model_type_dict()
        model_type = name_type_dict[args.model_name]
    
    with open(args.data_path, 'r', encoding='utf-8') as fin:
        ref = fin.readlines()
    total = len(ref)
    logger.info(f"Total number of lines: {total}")

    for line in ref:
        input_queue.put(line)

    counter = Value('i', 0)

    threads = []
    for _ in range(args.thread):
        t = threading.Thread(target=worker, args=(input_queue, output_queue, counter, total, model_type, args))
        t.start()
        threads.append(t)

    with open(save_path, 'w', encoding='utf-8') as fout:
        for _ in range(total):
            result = output_queue.get()
            if result:
                fout.write('[_mark_]' + result + '\n')

    for _ in range(args.thread):
        input_queue.put(None)

    for t in threads:
        t.join()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='eval whisper')
    parser.add_argument('--api_key',                help='',                           type=str)
    parser.add_argument('--is_azure',               action='store_true')
    parser.add_argument('--api_version',            default='2024-04-01-preview',      type=str)
    parser.add_argument('--azure_end_point',        help='',                           type=str)
    parser.add_argument('--max_token',              help='',                           type=int)
    parser.add_argument('--thread',                 help='',                           type=int)
    parser.add_argument('--model_name',             help='',                           type=str)
    parser.add_argument('--data_path',              help='',                           type=str)
    parser.add_argument('--save_dir',               help='',                           type=str)
    args = parser.parse_args()
    
    collect_data_from_gpt(args)

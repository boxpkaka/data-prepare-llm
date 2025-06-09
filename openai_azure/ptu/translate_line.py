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

src_lang = ""
tgt_lang = ""

def add_tranlate_prompt(text_in: str) -> str:
    
    if not src_lang or not tgt_lang:
        raise
    
    prompt = f"""
    Translate the following {src_lang} sentence into {tgt_lang}. Return the translation alongside the original {src_lang} sentence. Ensure the translation retains the original meaning and is fluent and natural, following the conventions and preferences of native speakers in the target language. Provide the translations in the following format, without any additional content.
    
    {src_lang}: {text_in}
    {tgt_lang}: 
    """

    return prompt
    
    
def fetch_translation(client, text,  model_type, args):
    prompt = add_tranlate_prompt(text_in=text)
    
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
                    logger.warning(f"Responsed nothing - {text}")
                    
                    return None
            
                result = get_translation_dict(text, message)
                return result
                
            elif model_type == 'completions':
                response = client.completions.create(
                    model=args.model_name,
                    prompt=prompt,
                    max_tokens=args.max_token
                )
                return response.choices[0].text.strip()
            
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
                output_queue.put(text)
                return
        
        except Exception as e:
            logger.error(f"Error fetching translation for {text}: {e}")
            output_queue.put(text)
            return


def get_translation_dict(ref_dict: Dict[str, str], response: str) -> Dict[str, str]:
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


def worker(input_queue, output_queue, model_type, args):
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
        fetch_translation(client, line, output_queue, model_type, args)
        input_queue.task_done()


def collect_data_from_gpt(args) -> None:
    global src_lang, tgt_lang
    
    src_lang = args.src_lang
    tgt_lang = args.tgt_lang
    
    logger.info(f"Translation: {src_lang} -> {tgt_lang}")
    
    if args.is_azure:
        client = openai.AzureOpenAI(
            azure_endpoint=args.azure_end_point,
            api_key=args.api_key,
            api_version=args.api_version,
        )
    else:
        client = openai.OpenAI(api_key=args.api_key)
        
    logger.success("Client has been created!")
    logger.info(f"Model: {args.model_name}")
    
    model_type = ''
    if not args.is_azure:
        name_type_dict = get_model_type_dict()
        model_type = name_type_dict[args.model_name]

    with open(args.data_path, 'r', encoding='utf-8') as fin:
        for line in fin:
            fetch_translation(
                text=line.strip(),
                
            )
        
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
    parser.add_argument('--data_path',               help='',                           type=str)
    parser.add_argument('--save_path',               help='',                           type=str)
    parser.add_argument('--src_lang',               help='',                           type=str)
    parser.add_argument('--tgt_lang',               help='',                           type=str)
    args = parser.parse_args()
    
    collect_data_from_gpt(args)

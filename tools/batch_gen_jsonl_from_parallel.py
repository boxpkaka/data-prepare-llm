from multiprocessing import Pool, cpu_count
from loguru import logger
from tqdm import tqdm
import ujson
import os

NEED_LANG = [
    "Portuguese", "Indonesian", "Hindi", "Telugu", "Tamil", "Urdu", "Vietnamese", "Malay", "Norwegian", "Swedish", "Finnish", 
    "Danish", "Dutch", "Catalan", "Hebrew", "Greek", "Hungarian", "Polish", "Czech", "Slovak", "Romanian", "Slovenian", 
    "Croatian", "Bulgarian", "Turkish", "Ukrainian", "Icelandic", "Filipino", "Swahili", "Mongolian", "Persian", "Kazakh", "Uzbek"
    ]

STYLE = [
    "sad", "chat", "calm", "angry", "sorry", "gentle", "serious", "fearful", "excited", "envious", "lyrical", "hopeful", "cheerful", "newscast", 
    "friendly", "shouting", "depressed", "terrified", "assistant", "unfriendly", "whispering", "empathetic", "disgruntled", "embarrassed", 
    "chat-casual", "conversation", "affectionate", "poetry-reading", "livecommercial", "newscast-formal", "customerservice", "newscast-casual", 
    "sports-commentary", "narration-relaxed", "advertisement-upbeat", "documentary-narration", "narration-professional", 
    "sports-commentary-excited"
]

SCENE = [
     "chat-casual", "conversation", "livecommercial", "sorry", "speech", "broadcast", "interviews"
]

LIMIT_REQUEST = 50000
MAX_FILE_SIZE = 99 * 1024 * 1024
MAX_TOKENS = 12000

PROMPT_PREFIX = "Translate the following English sentence into the specified languages. Return the translation alongside the original English sentence. Ensure the translation retains the original meaning and is fluent and natural, following the conventions and preferences of native speakers in the target language. Additionally, the scene and style must be selected from the provided sets, considering the context and tone of the English sentence. Provide the translations in the following format, including the original English sentence, the identified style, and scene without any additional content:"
PROMPT_SUFFIX = ': \n'.join(NEED_LANG) + ": "
STYLE_SUFFIX = "Style: [Choose one from: " + ', '.join(STYLE) + ']'
SCENE_SUFFIX = "Scene: [Choose one from: " + ', '.join(SCENE) + ']'


def get_prompted_text(text_in: str) -> str:
    text = f"{PROMPT_PREFIX}\n\nEnglish: {text_in}\n{PROMPT_SUFFIX}\n{STYLE_SUFFIX}\n{SCENE_SUFFIX}"
    return text


def convert_prompt(item: dict) -> str:
    sentence = item.get("en")
    if sentence:
        return get_prompted_text(sentence)
    else:
        return None


def split_list(lst, n):
    # 每个分割部分的大小
    k, m = divmod(len(lst), n)
    return [lst[i * k + min(i, m):(i + 1) * k + min(i + 1, m)] for i in range(n)]


def process_file(file_name: str, root_dir: str, output_dir: str, model_name: str) -> None:
    cnt = 0
    try:
        path_in = os.path.join(root_dir, file_name)
        path_out = os.path.join(output_dir, file_name)
        with open(path_in, 'r', encoding='utf-8') as fin, open(path_out, 'w', encoding='utf-8') as fout:
            for line in fin:
                items = ujson.loads(line)
                prompt = convert_prompt(items)
                if prompt is None:
                    continue
                uuid = items.get("id")
                messages = [
                    {
                        "role": "system",
                        "content": prompt
                    }
                ]
                dump_item = {
                    "custom_id":uuid,
                    "method": "POST",
                    "url": "/chat/completions",
                    "body": {
                        "model": model_name,
                        "messages": messages,
                        "max_tokens": MAX_TOKENS
                        },
                }
                ujson.dump(dump_item, fout, ensure_ascii=False)
                fout.write('\n')
                cnt += 1
        
        # 标记文件已处理完毕
        logger.success(f"file: {file_name} is done. ")
    except Exception as e:
        logger.error(f"{file_name}: {e}")

def process_single_config(
    process_file_names: list,
    root_dir: str,
    output_dir: str, 
    model_name: str
    ) -> None:
    # 使用多进程处理文件
    with Pool(processes=cpu_count()) as pool:
        logger.info(f"number of process file: {len(process_file_names)}")
        pool.starmap(process_file, [(file_name, root_dir, output_dir, model_name) for file_name in list(process_file_names)])

        pool.close()
        pool.join()

if __name__ == "__main__":
    root_dir = "/workspace/volume/data-skh/300-MT-Pro/data/supplement_c4_en_gpt4omini-21m-11/split"
    config_path = "/workspace/volume/data-skh/300-MT-Pro/workspace/data_prepare_gpt/config.json"
    
    all_file_names = os.listdir(root_dir)
    all_file_names = sorted(all_file_names)

    with open(config_path, 'r', encoding='utf-8') as f:
        configs = ujson.load(f)
        nums = len(list(configs.keys()))
        process_file_names = split_list(all_file_names, nums)
        for index, config_name in enumerate(configs.keys()):
            config = configs.get(config_name)
            if config is None:
                raise Exception(f"Should provide correct config name, not {config}")
            
            model_name = config.get('model_name')
            output_dir = config.get('data_dir')

            process_single_config(
                process_file_names=process_file_names[index],
                root_dir=root_dir,
                output_dir=output_dir, 
                model_name=model_name
                )
            logger.success(config_name)

    
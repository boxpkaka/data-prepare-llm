from multiprocessing import Pool, cpu_count
from loguru import logger
from tqdm import tqdm
import ujson
import os

NEED_LANG = [
    "Chinese", "Spanish", "Japanese", "Korean", "Thai", "Arabic","German", "French", "Italian", "Russian", "Portuguese", "Indonesian",
    "Hindi", "Telugu", "Tamil", "Urdu", "Vietnamese", "Malay", "Norwegian", "Swedish", "Finnish", "Danish", "Dutch", "Catalan", "Hebrew",
    "Greek", "Hungarian", "Polish", "Czech", "Slovak", "Romanian", "Slovenian", "Croatian", "Bulgarian", "Turkish", "Ukrainian", "Icelandic", 
    "Filipino", "Swahili", "Mongolian", "Persian", "Kazakh", "Uzbek"
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

PROMPT_PREFIX = "Translate the following English sentence into the specified languages. Return the translation alongside the original English sentence. Ensure the translation retains the original meaning and follows the word order of the English sentence, while maintaining grammatical correctness and fluency. Additionally, choose the most appropriate style and scene from the provided sets, considering the context and tone of the English sentence. Provide the translations in the following format, including the original English sentence, the identified style, and scene without any additional content:"
PROMPT_SUFFIX = ': \n'.join(NEED_LANG) + ": "
STYLE_SUFFIX = "Style: [Choose one from: " + ', '.join(STYLE) + ']'
SCENE_SUFFIX = "Scene: [Choose one from: " + ', '.join(SCENE) + ']'

def get_prompted_text(text_in: str) -> str:
    text = f"{PROMPT_PREFIX}\n\nEnglish: {text_in}\n{PROMPT_SUFFIX}\n{STYLE_SUFFIX}\n{SCENE_SUFFIX}"
    return text

def convert_prompt(origin: str) -> str:
    sentence = origin.split("English: ")[-1].split("Chinese: ")[0].strip()
    return get_prompted_text(sentence)

def process_file(file_name: str, root_dir: str, output_dir: str, completion_file_path: str) -> None:
    cnt = 0
    try:
        path_in = os.path.join(root_dir, file_name)
        path_out = os.path.join(output_dir, file_name)
        with open(path_in, 'r', encoding='utf-8') as fin, open(path_out, 'w', encoding='utf-8') as fout:
            for line in fin:
                origin_prompt = ujson.loads(line)["body"]["messages"][0]["content"]
                prompt = convert_prompt(origin_prompt)
                dump_item = {
                    f"{cnt:04}": prompt
                }
                ujson.dump(dump_item, fout, ensure_ascii=False)
                fout.write('\n')
                cnt += 1
        
        # 标记文件已处理完毕
        logger.success(f"file: {file_name} is done. ")
        with open(completion_file_path, 'a', encoding='utf-8') as f_check:
            f_check.write(file_name + '\n')
    except Exception as e:
        logger.error(f"{file_name}: {e}")

def main(root_dir: str, output_dir: str, converted_id_file: str):
    os.makedirs(output_dir, exist_ok=True)
    completion_file_path = os.path.join(output_dir, 'completion.txt')
    if not os.path.exists(completion_file_path):
        os.system(r"touch {}".format(completion_file_path))
        logger.info(f"generate complete file: {completion_file_path}")
    
    # 已完成文件=已处理+converted_id.json
    completions = set()
    with open(completion_file_path, 'r', encoding='utf-8') as f_check:
        for file_name in f_check:
            completions.add(file_name.strip())
    with open(converted_id_file, 'r', encoding='utf-8') as f_converted:
        converted_ids = ujson.load(f_converted)
        for file_name in converted_ids:
            completions.add(file_name.strip())

    process_file_names = set(os.listdir(root_dir)) - completions
    process_file_names = sorted(list(process_file_names))[3000:3500]

    # 使用多进程处理文件
    with Pool(processes=cpu_count()) as pool:
        logger.info(f"number of process file: {len(process_file_names)}")
        pool.starmap(process_file, [(file_name, root_dir, output_dir, completion_file_path) for file_name in list(process_file_names)])

        pool.close()
        pool.join()

if __name__ == "__main__":
    output_dir = "/workspace/volume/data-skh/300-MT-Pro/data/c4/en_gemini"
    
    root_dir = "/workspace/volume/data-skh/300-MT-Pro/data/c4/en_batch_api/11-lang"
    converted_id_file = "/workspace/volume/data3-lianxiang/300-MT-Pro/data_prepare_gpt/log/batch-11-lang/converted_id.json"
    main(root_dir, output_dir, converted_id_file)

    
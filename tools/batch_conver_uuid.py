import ujson
import os
from concurrent.futures import ProcessPoolExecutor

NEED_LANG = [
    "pt", "id", "hi", "te", "ta", "ur", "vi", "ms", "no", "sv", "fi", "da", "nl", "ca", "he", "el", "hu", "pl", "cs", "sk", "ro", "sl", "hr", "bg", "tr", "uk", "is", "fil", "sw", "mn", "fa", "kk", "uz"
]


ORIGIN_DIR = "/workspace/volume/data-skh/300-MT-Pro/data/supplement_c4_en_gpt4omini-21m-11/split"
OUTPUT_DIR = "/workspace/volume/data-skh/300-MT-Pro/data/supplement_c4_en_gpt4omini-21m-11/supplemented"

def supplement(need_name: str) -> None:
    origin_path = os.path.join(ORIGIN_DIR, need_name)
    target_path = os.path.join(OUTPUT_DIR, need_name)
    
    with open(origin_path, 'r', encoding='utf-8') as fin, \
        open(target_path, 'w', encoding='utf-8') as fout:
        for line in fin:
            orig_item = ujson.loads(line)
            orig_item["uuid"] = orig_item.get("id")
            for lang in NEED_LANG:
                if orig_item.get(lang) is None:
                    orig_item[lang] = ""
            ujson.dump(orig_item, fout, ensure_ascii=False)
            fout.write('\n')
            

def main():
    origin_names = set(os.listdir(ORIGIN_DIR))
    target_names = set(os.listdir(OUTPUT_DIR))
    
    need_names = list(origin_names - target_names)
    
    # 使用 ProcessPoolExecutor 进行多进程处理
    with ProcessPoolExecutor() as executor:
        executor.map(supplement, need_names)

if __name__ == "__main__":
    main()

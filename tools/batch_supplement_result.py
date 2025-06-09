import ujson
import os
from concurrent.futures import ProcessPoolExecutor

NEED_LANG = [
    "pt", "id", "hi", "te", "ta", "ur", "vi", "ms", "no", "sv", "fi", "da", "nl", "ca", "he", "el", "hu", "pl", "cs", "sk", "ro", "sl", "hr", "bg", "tr", "uk", "is", "fil", "sw", "mn", "fa", "kk", "uz", "style", "scene"
]

SPECIAL_ITEM = [
    ""
]

ORIGIN_DIR = "/workspace/volume/data-skh/300-MT-Pro/data/supplement_c4_en_gpt4omini-21m-11/split"
TARGET_DIR = "/workspace/volume/data-skh/300-MT-Pro/data/supplement_c4_en_gpt4omini-21m-11/batch_api/"
OUTPUT_DIR = "/workspace/volume/data-skh/300-MT-Pro/data/supplement_c4_en_gpt4omini-21m-11/supplemented"

def supplement(config_name: str) -> None:
    target_dir = os.path.join(TARGET_DIR, config_name, "parallel")
    for file_name in os.listdir(target_dir):
        if "c4_en-gpt4omini-21m-11" not in file_name:
            continue
        origin_path = os.path.join(ORIGIN_DIR, file_name)
        target_path = os.path.join(target_dir, file_name)
        output_path = os.path.join(OUTPUT_DIR, file_name)

        with open(origin_path, 'r', encoding='utf-8') as f_orig, \
                open(target_path, 'r', encoding='utf-8') as f_tar, \
                open(output_path, 'w', encoding='utf-8') as f_out:
            target_dict = {}
            for line in f_tar:
                item = ujson.loads(line)
                target_dict[item.get("uuid")] = item

            for line in f_orig:
                orig_item = ujson.loads(line)
                uuid = orig_item.get("id")
                supple_items = target_dict.get(uuid)
                if supple_items:
                    for lang in NEED_LANG:
                        orig_item[lang] = supple_items.get(lang)
                orig_item["uuid"] = uuid
                ujson.dump(orig_item, f_out, ensure_ascii=False)
                f_out.write("\n")

def main():
    config_names = [config_name for config_name in os.listdir(TARGET_DIR)]
    
    # 使用 ProcessPoolExecutor 进行多进程处理
    with ProcessPoolExecutor() as executor:
        executor.map(supplement, config_names)

if __name__ == "__main__":
    main()

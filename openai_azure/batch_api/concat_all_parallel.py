import ujson
import os
import argparse

from loguru import logger

FILE_PATHS = []

def add_paths(completions_path: str) -> None:
    with open(completions_path, 'r', encoding='utf-8') as f:
        items = ujson.load(f)
    
    data_dir = os.path.dirname(completions_path)
    for file_name in items.keys():
        if file_name.endswith("jsonl"):
            FILE_PATHS.append(os.path.join(data_dir, file_name))

def concat(output_path: str) -> None:
    temp_file_list = "file_list.txt"
    with open(temp_file_list, "w") as f:
        for file_path in FILE_PATHS:
            f.write(f"{file_path}\n")
            
    cat_command = f"xargs cat < {temp_file_list} > {output_path}"
    logger.info(f"Save in {output_path}")
    os.system(cat_command)
    os.remove(temp_file_list)
    logger.success("Done. ")

def main(args):
    with open(args.config_path, 'r', encoding='utf-8') as f:
        configs = ujson.load(f)
    
    for config_name, config in configs.items():
        data_dir = config.get("data_dir")
        completions_path = os.path.join(data_dir, "parallel", "completions.json")
        add_paths(completions_path)
    
    concat(args.output_path)
    

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config_path",     help="", type=str)
    parser.add_argument("--output_path",     help="", type=str)
    args = parser.parse_args()

    main(args)



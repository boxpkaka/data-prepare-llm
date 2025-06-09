import os
from typing import List

import ujson
from loguru import logger
from pathlib import Path


class FileLock:
    def __init__(self, lock_file):
        self.lock_file = lock_file + ".lock"

    def acquire(self):
        if os.path.exists(self.lock_file):
            raise Exception(f"File: {self.lock_file[:-5]} is locking.")
        with open(self.lock_file, "w") as f:
            f.write("locked")

    def release(self):
        if os.path.exists(self.lock_file):
            os.remove(self.lock_file)
        else:
            logger.warning(f"锁文件 {self.lock_file} 不存在，跳过释放锁。")

    def __enter__(self):
        self.acquire()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()


def write_json_file(path: str, key: str, value):
    with open(path, "r+", encoding="utf-8") as f:
        try:
            origin = ujson.load(f)
        except Exception:
            origin = {}
        origin[key] = value
        f.seek(0)  # 重置文件指针到开头
        f.truncate()  # 截断文件以删除旧内容
        ujson.dump(origin, f, ensure_ascii=False, indent=4)


def check_json_files_exist(paths: List[str] | str) -> None:
    if isinstance(paths, str):
        if not os.path.exists(paths):
            with open(paths, "w", encoding="utf-8") as f_failed:
                ujson.dump({}, f_failed, ensure_ascii=False, indent=4)
            return
        else:
            return
    for path in paths:
        if not os.path.exists(path):
            with open(path, "w", encoding="utf-8") as f_failed:
                ujson.dump({}, f_failed, ensure_ascii=False, indent=4)
            return
        else:
            return


def read_config(config_path: str, config: str) -> dict:
    with open(config_path, "r", encoding="utf-8") as f:
        config = ujson.load(f).get(config)
        if config is None:
            raise Exception(f"Should provide correct config name, not {config}")
    return config


def create_lock(lock_file: str):
    with open(lock_file, "w") as lock:
        lock.write("locked")


def remove_lock(lock_file: str):
    os.remove(lock_file)


def deep_update(orig: dict, new: dict) -> dict:
    """
    对 orig 进行深度更新，遍历 new 的每个键：
    - 如果 orig 中对应键的值也是字典，则递归更新
    - 如果类型不同或值不同，则直接覆盖
    """
    for key, new_val in new.items():
        if key in orig:
            old_val = orig[key]
            if isinstance(old_val, dict) and isinstance(new_val, dict):
                orig[key] = deep_update(old_val, new_val)
            else:
                # 当类型不同或者值不同，则更新
                if type(old_val) != type(new_val) or old_val != new_val:
                    orig[key] = new_val
        else:
            orig[key] = new_val
    return orig

def write_json(
    json_path: Path | str, 
    dump_item: dict,
    overwrite: bool = False
) -> None:
    if isinstance(json_path, str):
        json_path = Path(json_path)
    
    # 检查文件是否存在
    if not json_path.exists():
        json_path.parent.mkdir(parents=True, exist_ok=True)
        with open(json_path, "w", encoding="utf-8") as f:
            ujson.dump({}, f, ensure_ascii=False, indent=4)
    
    # Overwrite 模式直接覆盖
    if overwrite:
        try:
            with open(json_path, "w", encoding="utf-8") as f:
                ujson.dump(dump_item, f, ensure_ascii=False, indent=4)
        except Exception as e:
            logger.error(f"JSON WRITE Error: {json_path} - {e}")
        return
    
    # Update 模式进行深度更新
    with open(json_path, "r+", encoding="utf-8") as f:
        try:
            data = ujson.load(f)
        except Exception as e:
            logger.error(f"JSON LOADING ERROR: {e}")
            data = {}

        # 使用递归函数更新嵌套字典
        updated_data = deep_update(data, dump_item)
        f.seek(0)
        f.truncate()
        ujson.dump(updated_data, f, ensure_ascii=False, indent=4)


def read_json(json_path: str) -> dict:
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            return ujson.load(f)
    except Exception as e:
        logger.error(f"JSON READ Error: {json_path} - {e}")
        return {}

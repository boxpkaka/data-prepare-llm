from typing import List
from loguru import logger
import ujson
import os


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
    with open(config_path, 'r', encoding='utf-8') as f:
        config = ujson.load(f).get(config)
        if config is None:
            raise Exception(f"Should provide correct config name, not {config}")
    return config

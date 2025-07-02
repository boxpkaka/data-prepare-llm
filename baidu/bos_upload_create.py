"""
作业限制：
 - 任务数量：100个
 - 单个任务文件数量：100个
 - 单个任务累积文件大小：300MB

目录格式
 - 主目录 (任务名)
   - 子目录1（任务名1）
   - ...
"""

from baidu.bos_client import BOSClient
from tools.batch_gen_request import parse_args
from utils.io import read_config
from pathlib import Path
import os
import re
import shutil
from loguru import logger

TASK_LIMIT = 100
FILE_LIMIT = 50

def get_suffix_num(filename):
    # 使用正则表达式匹配下划线后面的数字直到文件扩展名前的部分
    match = re.search(r'_(\d+)\.', filename)
    return int(match.group(1)) if match else 0

def create_sub_dir(batch_dir: Path, task_name: str):
    all_names = [name for name in os.listdir(batch_dir) if name.endswith(".jsonl")]
    sorted_names = sorted(all_names, key=get_suffix_num)

    task_index = 0
    file_num = 0
    for name in sorted_names:
        if file_num >= FILE_LIMIT:
            task_index += 1
            file_num = 0

        sub_dir = batch_dir / f"{task_name}_{task_index}"
        os.makedirs(sub_dir, exist_ok=True)

        src_path = batch_dir / name
        tgt_path = sub_dir / name

        if tgt_path.exists():
            continue

        shutil.move(src=src_path, dst=tgt_path)
        file_num += 1

def main():
    args = parse_args()
    config = read_config(
        config_path=args.config_path,
        config=args.config_name
    )

    data_dir = Path(config.get("data_dir"))
    assert data_dir.exists()

    bos_client = BOSClient(
        config_path=args.config_path,
        config_name=args.config_name,
        inference_endpoint_name=""
    )

    logger.info("Creating sub directory.")
    create_sub_dir(
        batch_dir=data_dir / "batch_api",
        task_name=data_dir.name
        )

    logger.info("Creating batch job.")
    sub_dirs = [
        data_dir / "batch_api"/ sub_dir_name 
        for sub_dir_name in os.listdir(data_dir / "batch_api") 
        if (data_dir / "batch_api"/ sub_dir_name).is_dir()
        ]

    for sub_dir in sub_dirs:
        bos_client.create_batch_job_local(
            local_dir=sub_dir,
            main_task_name=data_dir.name,
            sub_task_name=sub_dir.name.replace("-", "_"),
            overwrite=False
        )


if __name__ == "__main__":
    main()


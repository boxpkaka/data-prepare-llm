import argparse
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import List

import openai
import ujson
from loguru import logger
from openai import AzureOpenAI
from safe_read_write import check_json_files_exist, read_config


def upload_create_file(client, file_path) -> None:
    back_off_time = 3
    file_id = None
    while True:
        try:
            logger.info(f"Try to upload: {file_path}")
            batch_file = client.files.create(
                file=open(file_path, "rb"), purpose="batch"
            )
            logger.info(f"上传成功: {file_path} - file id: {batch_file.id}")
            file_id = batch_file.id
            break
        except openai.BadRequestError as e:
            error_message = str(e)
            if "quotaExceeded" in error_message:
                logger.error(f"Reached the limit: {e}")
                logger.info("Exiting. ")
                return
            time.sleep(back_off_time)
            continue
        except Exception as e:
            logger.warning(f"文件上传失败: {e} - {file_path}")
            raise

    while True:
        try:
            logger.info(f"Try to create: {file_path}")
            batch = client.batches.create(
                input_file_id=file_id,
                endpoint="chat/completions",
                completion_window="24h",
                metadata={
                    "dataset": "C4/en",
                    "name": file_path,
                    "num_lang": str(44),
                    "style": str(True),
                    "scene": str(True),
                    "time": str(datetime.now().strftime("%Y-%m-%d %H-%M-%S")),
                },
            )
            # check metadata exist
            check_batch = client.batches.retrieve(batch.id)
            if check_batch.metadata is None:
                logger.error(f"Metadata is null, cancel and delete file: {file_path}")
                client.batches.cancel(batch.id)
                client.files.delete(batch.input_file_id)
                raise
            metadata_name = check_batch.metadata.get("name")
            logger.success(f"作业创建成功: {file_path} - filepath: {metadata_name}")
            return file_id, batch.id, batch.status
        except Exception as e:
            logger.warning(f"作业创建失败: {e} - {file_path}")
            logger.info(f"Retry after {back_off_time}s. ")
            time.sleep(back_off_time)
            continue


def get_need_upload_file_names(id_file: str, data_dir: str) -> List[str]:
    file_names = [name for name in os.listdir(data_dir) if name.endswith("jsonl")]
    with open(id_file, "r", encoding="utf-8") as f_ids:
        try:
            ids = ujson.load(f_ids)
        except Exception as e:
            logger.warning(f"{id_file} is null. ")
            ids = {}
        uploaded_file_names = set(ids.keys())

    need_file_names = list(set(file_names) - uploaded_file_names)
    
    if len(need_file_names) == 0:
        logger.warning("已没有文件需要上传")
    
    return need_file_names


def process_file(client, data_path):
    file_id, batch_id, status = upload_create_file(client, data_path)
    save_item = {
        "file_id": file_id,
        "batch_id": batch_id,
        "status": status,
    }
    return save_item


def main(args):
    
    # read config
    config = read_config(config_path=args.config_path, config=args.config)
    
        
    client = AzureOpenAI(
        api_key=config.get("api_key"),
        api_version="2024-07-01-preview",
        azure_endpoint=config.get("azure_endpoint"),
    )

    id_file = config.get("id_file")
    data_dir = config.get("data_dir")
    check_json_files_exist(id_file)
    need_file_names = get_need_upload_file_names(id_file, data_dir)
    
    num_workers = args.num_workers
    with ThreadPoolExecutor(
        max_workers=num_workers
    ) as executor: 
        futures = [
            executor.submit(
                process_file, client, os.path.join(args.data_dir, name), id_file
            )
            for name in need_file_names
        ]

        for future in as_completed(futures):
            try:
                future.result()
            except Exception as e:
                logger.error(f"文件处理过程中发生错误: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config_path",    help="",  type=str)
    parser.add_argument("--config",         help="",  type=str)
    parser.add_argument("--num_workers",    help="",  type=int)
    args = parser.parse_args()

    main(args)

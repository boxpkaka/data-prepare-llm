import argparse
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

import ujson
from openai import APITimeoutError
from loguru import logger
from openai import AzureOpenAI
from safe_read_write import read_config
from upload_create_batch import (
    check_json_files_exist,
    get_need_upload_file_names,
    upload_create_file,
)


class BatchMonitor(object):
    def __init__(
        self,
        config_path: str,
        config_name: str,
        max_workers: int,
        max_inpro_val: int,
        batch_limit: int = 100,
        max_page: int = 100,
        upload: bool = False,
        download: bool = False,
        after_date: str = None,
    ):
        self.max_workers = max_workers
        self.max_inpro_val = max_inpro_val
        self.upload = upload
        self.download = download
        self.batch_limit = batch_limit
        self.max_page = max_page
        self.after_date = after_date
        
        self.client = None
        self.data_dir = None
        self.save_dir = None
        self.id_file = None
        self.id_file_infos = None
        self.record_items = []

        self.init_config(config_path=config_path, config_name=config_name)

    def init_config(self, config_path: str, config_name: str) -> None:
        config = read_config(config_path=config_path, config=config_name)
        self.client = AzureOpenAI(
            api_key=config.get("api_key"),
            api_version=config.get("api_version"),
            azure_endpoint=config.get("azure_endpoint"),
        )
        self.data_dir = config.get("data_dir")
        self.id_file = config.get("id_file")
        self.save_dir = os.path.join(self.data_dir, "gpt")
        os.makedirs(self.save_dir, exist_ok=True)
        check_json_files_exist(self.id_file)
        
        if self.after_date:
            logger.info(f"Filter all batches before {self.after_date}")
            self.after_date = datetime.strptime(self.after_date, "%Y-%m-%dT%H:%M:%S")
            self.after_date = int(time.mktime(self.after_date.timetuple()))
        else:
            self.after_date = 0
            
        # setup_logger
        date_time = datetime.now().strftime("%Y-%m-%d-%H:%M:%S")
        log_dir = os.path.dirname(self.id_file)
        log_file = os.path.join(log_dir, f"Monitor-{config_name}-{date_time}.log")
        logger.add(log_file, level="DEBUG", rotation="10 MB")

    def update_id_file(self) -> None:
        if self.record_items:
            logger.info(f"Wirting id infos in {self.id_file}")
            with open(self.id_file, "w", encoding="utf-8") as f:
                dump_item = {k: v for d in self.record_items for k, v in d.items()}
                ujson.dump(dump_item, f, ensure_ascii=False, indent=4)
        logger.info(f"get ids infos from {self.id_file}")
        with open(self.id_file, "r", encoding="utf-8") as f:
            self.id_file_infos = ujson.load(f)

    def delete_file(self, file_id, file_name=None) -> None:
        if not file_name:
            file_name = "Null"
        try:
            self.client.files.delete(file_id)
            logger.info(f"文件: {file_name}-{file_id} 已删除")
        except Exception as e:
            logger.info(f"文件删除失败: {file_name}-{file_id}-{e}")

    def download_file(self, output_file_id: str, output_path: str) -> None:
        try:
            logger.info(f"Downloading: {output_path}")
            content = self.client.files.content(output_file_id)
            with open(output_path, "wb") as f:
                f.write(content.read())
            logger.success(f"结果文件已下载: {output_path}")
        except Exception as e:
            logger.warning(f"结果文件下载失败: {e}")
            raise

    def get_file_status(self, item, file_name: str = None) -> str:
        if file_name:
            file_info = self.id_file_infos.get(file_name)
            if file_info:
                past_file_status = file_info.get("file_status")
                if past_file_status == "Deleted":
                    return past_file_status
        try:
            file_infos = self.client.files.retrieve(item.input_file_id)
            file_status = file_infos.status
            return file_status
        except Exception:
            return "Deleted"

    def update_batches_list(self, next_after):
        back_off_time = 1
        while True:
            try:
                if next_after:
                    batches = self.client.batches.list(
                        limit=self.batch_limit, after=next_after
                    )
                else:
                    batches = self.client.batches.list(limit=self.batch_limit)
                return batches
            except APITimeoutError as e_timeout:
                logger.error(f"{e_timeout}, try after {back_off_time * 10}s. ")
                time.sleep(back_off_time * 10)
                continue
            except Exception as e:
                if "429" in str(e):
                    logger.warning(f"Request limit: {e}, try after {back_off_time}s. ")
                    time.sleep(back_off_time)
                    continue
                else:
                    logger.error(f"Error: {e}")
                    return None

    def process_file(self, item) -> dict | None:
        batch_id = item.id
        file_id = item.input_file_id
        batch_status = item.status
        output_file_id = item.output_file_id

        if batch_status in {"cancelling", "cancelled", "failed"}:
            # print(item.errors.data)
            # fail_message = item.errors.message
            logger.warning(f"{batch_status} - {item.errors.data}")
            return None

        if item.created_at < self.after_date:
            return None
        
        # get filename from metadata
        detailed_batch = self.client.batches.retrieve(batch_id)
        metadata = detailed_batch.metadata
        if metadata:
            file_name = os.path.basename(metadata.get("name"))
        else:
            logger.error("Can't get metadata")
            if self.download:
                logger.error(f"Cancelling file: {batch_id}")
                self.client.batches.cancel(batch_id)
                self.delete_file(file_id, None)
            return None

        output_path = os.path.join(self.save_dir, file_name)
        record_item = {
            file_name: {
                "batch_id": batch_id,
                "file_id": file_id,
                "status": batch_status,
                "file_status": None,
                "completed_at": item.completed_at,
                "expires_at": item.expires_at,
                "metadata": metadata,
                "completed": item.request_counts.completed,
                "failed": item.request_counts.failed,
                "total": item.request_counts.total,
            }
        }
        if batch_status == "completed":
            logger.success(f"{file_name} is completed. ")
            file_status = self.get_file_status(item=item, file_name=file_name)
            if file_status != "Deleted":
                if self.download:
                    self.download_file(output_file_id, output_path)
                    self.delete_file(file_id, file_name)
                    record_item[file_name]["file_status"] = "Deleted"
                else:
                    logger.info("Skip download. ")
            else:
                record_item[file_name]["file_status"] = file_status
        elif batch_status == "expired":
            logger.warning(
                f"{batch_status} - {file_name} - completed: {item.request_counts.completed}/{item.request_counts.total}"
            )
            file_status = self.get_file_status(item=item, file_name=file_name)
            if file_status != "Deleted":
                if self.download:
                    self.download_file(output_file_id, output_path)
                    self.delete_file(file_id, file_name)
                    record_item[file_name]["file_status"] = "Deleted"
                else:
                    logger.info("Skip download. ")
            else:
                record_item[file_name]["file_status"] = file_status
        else:
            logger.info(f"{file_name}: {batch_status}")

        return record_item

    def get_page_infos(self, executor, batches) -> tuple:
        futures = [executor.submit(self.process_file, item) for item in batches.data]
        
        num_inpro_val = 0
        for future in as_completed(futures):
            try:
                result = future.result()  # 获取返回值
                if result:
                    file_name = list(result.keys())[0]
                    infos = result.get(file_name)
                    if infos.get("status") in {"in_progress", "validating"}:
                        num_inpro_val += 1
                    self.record_items.append(result)
            except Exception as e:
                logger.error(f"Error processing file: {e}")
                # 服务器不可用
                if "503 Service" in str(e):
                    continue

        return num_inpro_val

    def upload_by_inprocess_num(self, num_inpro_val: int) -> None:
        logger.info(f"Number of in_process file: {num_inpro_val}")
        if num_inpro_val < self.max_inpro_val:
            if self.upload:
                need_upload_num = self.max_inpro_val - num_inpro_val
                upload_file_names = get_need_upload_file_names(
                    id_file=self.id_file, data_dir=self.data_dir
                )
                need_upload_num = min(need_upload_num, len(upload_file_names))
                
                file_paths = [
                    os.path.join(self.data_dir, name)
                    for name in upload_file_names[:need_upload_num]
                ]
                
                logger.info(f"Uploading {need_upload_num} files.")
                for file_path in file_paths:
                    try:
                        file_id, batch_id, batch_status = upload_create_file(client=self.client, file_path=file_path)
                        file_name = os.path.basename(file_path)
                        
                        record_item = {
                            file_name: {
                                "batch_id": batch_id,
                                "file_id": file_id,
                                "status": batch_status,
                                "file_status": "created",
                                "completed_at": None,
                                "expires_at": None,
                                "metadata": None,
                                "completed": 0,
                                "failed": 0,
                                "total": 0,
                            }
                        }
                        
                        self.record_items.append(record_item)
                         
                    except Exception as e:
                        logger.error(f"Upload error: {file_path} - {e}")
            else:
                logger.info("Skip upload. ")

    def start_monitor(self):
        logger.info("Start minitor. ")
        # open upload or download mode
        if self.upload:
            logger.info("Minitor will upload file. ")
        if self.download:
            logger.info("Minitor will download file.")

        # start monitor
        logger.info(f"Using {self.max_workers} threads for processing.")
        logger.info(f"Id file: {os.path.basename(self.id_file)}")
        self.update_id_file()
        while True:
            next_after = None
            page = 0
            num_inpro_val = 0
            self.record_items = []
            self.update_id_file()
            # Start one round
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                while True:
                    # update current batches list
                    batches = self.update_batches_list(next_after=next_after)
                    
                    if batches is None:
                        break
                    
                    if len(batches.data) != 0:
                        # break if batch created before after_date
                        if batches.data[0].created_at < self.after_date:
                            logger.info(f"Skip batches before timestamp: {self.after_date}")
                            break
                        
                        # get batches information from current batches
                        num_inpro_val_page = self.get_page_infos(
                            executor=executor,
                            batches=batches,
                        )

                        # update number of file which's status is <in_process> or <validating>
                        num_inpro_val += num_inpro_val_page
                        
                        # get next start batches of next list if it exist
                        if batches.has_more and page != self.max_page:
                            next_after = batches.data[-1].id
                        else:
                            break

                        # go next page
                        page += 1
                        logger.info(f"Page-{page}")
                    # end if
                    else:
                        num_inpro_val = 0
                        break
                # end While
            # end with
            
            # if on upload mode, try to upload new file
            self.upload_by_inprocess_num(
                num_inpro_val=num_inpro_val
                )

            # update id file
            self.update_id_file()

            # waiting
            logger.info("Waiting...")
            time.sleep(60)


def main(args):
    monitor = BatchMonitor(
        config_path=args.config_path,
        config_name=args.config,
        max_workers=args.max_workers,
        max_inpro_val=args.max_inpro_val,
        upload=args.upload,
        download=args.download,
        after_date=args.after_date
    )
    monitor.start_monitor()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config_path",    help="", type=str)
    parser.add_argument("--config",         help="", type=str)
    parser.add_argument("--max_workers",    help="", type=int)
    parser.add_argument("--max_inpro_val",  help="", type=int)
    parser.add_argument("--after_date",     help="", type=str, default=None)
    parser.add_argument("--upload",         action="store_true")
    parser.add_argument("--download",       action="store_true")
    args = parser.parse_args()

    main(args)

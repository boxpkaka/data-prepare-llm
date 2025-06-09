import os
import ujson
import argparse
from datetime import datetime, timedelta, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed
from loguru import logger
from openai import AzureOpenAI
from safe_read_write import write_json_file, read_config, check_json_files_exist


class AzureBatchManager:
    def __init__(self, config: dict):
        self.config = config
        self.id_file = config.get("id_file")
        check_json_files_exist(self.id_file)
        self.client = AzureOpenAI(
            api_key=config.get("api_key"),
            api_version="2024-07-01-preview",
            azure_endpoint=config.get("azure_endpoint")
        )

    @staticmethod
    def timestamp_to_cntime(timestamp: int) -> str:
        utc_time = datetime.fromtimestamp(timestamp, tz=timezone.utc)
        cn_timezone = timezone(timedelta(hours=8))
        cn_time = utc_time.astimezone(cn_timezone).strftime('%Y-%m-%d %H:%M:%S')
        return cn_time

    def delete_file(self, file_id) -> None:
        try:
            self.client.files.delete(file_id)
            logger.info(f"文件 {file_id} 已删除")
        except Exception as e:
            logger.info(f"文件删除失败: {e}")

    def get_unfailed_batch_record(self, batch_item) -> dict | None:
        if batch_item.status != "failed":
            try:
                file_infos = self.client.files.retrieve(batch_item.input_file_id)
                file_status = file_infos.status
            except Exception:
                file_status = "Deleted"
            file_name = os.path.basename(batch_item.metadata["name"])
            record_item = {
                "batch_id": batch_item.id,
                "file_id": batch_item.input_file_id,
                "status": batch_item.status,
                "file_status": file_status
            }
            print(file_name)
            print(record_item)
            return {file_name: record_item}
        else:
            print(batch_item)
            return None

    def check_status_of_undelete_file(self, batch_item) -> None:
        batch_status = batch_item.status
        try:
            file_infos = self.client.files.retrieve(batch_item.input_file_id)
            create_time = self.timestamp_to_cntime(file_infos.created_at)
            file_status = file_infos.status
        except Exception:
            file_status = "Deleted"
            create_time = 'Null'
        logger.info(
            f"batch status: {batch_status} - file status: {file_status} - create time: {create_time} - batch id: {batch_item.id}"
        )

    def check_no_failed_batch(self, batch_item) -> None:
        if batch_item.status not in {"failed"}:
            logger.info(batch_item)

    def write_unfailed_ids(self, batches, max_workers=4) -> None:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [
                executor.submit(self.get_unfailed_batch_record, batch_item)
                for batch_item in batches.data
            ]
            record_items = []
            for future in as_completed(futures):
                result = future.result()
                if result:
                    record_items.append(result)
            for record in record_items:
                for key, value in record.items():
                    write_json_file(self.id_file, key, value)

    def cancel_processing_batches(self, batches) -> None:
        with open(self.id_file, 'r+', encoding='utf-8') as f_id:
            file_ids = ujson.load(f_id)
            for batch_item in batches.data:
                if batch_item.metadata.get("name") is None:
                    continue
                if batch_item.status not in {'in_progress', 'validating'}:
                    continue
                self.client.batches.cancel(batch_item.id)
                self.delete_file(batch_item.input_file_id)
                file_name = os.path.basename(batch_item.metadata["name"])
                if (
                    file_name in file_ids and
                    batch_item.id == file_ids[file_name]['batch_id'] and
                    batch_item.input_file_id == file_ids[file_name]["file_id"]
                ):
                    del file_ids[file_name]
            f_id.seek(0)
            f_id.truncate()
            ujson.dump(file_ids, f_id, ensure_ascii=False, indent=4)

    def delete_failed_file(self, batches) -> None:
        for batch_item in batches.data:
            if batch_item.status == "failed":
                self.delete_file(batch_item.input_file_id)

    def check_status_batches(self, batches) -> None:
        for batch_item in batches.data:
            self.check_status_of_undelete_file(batch_item)

    def check_no_failed_batches(self, batches) -> None:
        for batch_item in batches.data:
            self.check_no_failed_batch(batch_item)

    def list_all_batches(self, action: str, batch_limit=100, max_workers=4) -> None:
        """
        List batches page by page and perform the specified action on each batch page.
        The action parameter is a string that selects which batch operation to execute.
        All operation functions take a 'batches' object as their sole argument.
        """
        action_map = {
            "delete_failed": self.delete_failed_file,
            "cancel_processing": self.cancel_processing_batches,
            "write_unfailed": lambda batches: self.write_unfailed_ids(batches, max_workers=max_workers),
            "check_status": self.check_status_batches,
            "check_no_failed": self.check_no_failed_batches,
        }
        if action not in action_map:
            logger.error(f"Unrecognized action: {action}")
            return

        next_after = None
        cnt = 0
        while True:
            if next_after:
                batches = self.client.batches.list(limit=batch_limit, after=next_after)
            else:
                batches = self.client.batches.list(limit=batch_limit)

            # Execute the chosen action on the current batch page.
            action_map[action](batches)

            if batches.has_more:
                next_after = batches.data[-1].id
            else:
                break
            cnt += 1
            print(f"Page {cnt} processed.")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config_path', help='', type=str)
    parser.add_argument('--config', help='', type=str)
    parser.add_argument('--action', help='指定对batch作业的操作', type=str, required=True)
    args = parser.parse_args()

    config = read_config(config_path=args.config_path, config=args.config)
    manager = AzureBatchManager(config)
    manager.list_all_batches(action=args.action)


if __name__ == "__main__":
    main()

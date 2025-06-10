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
from utils.io import read_config, write_json
from pathlib import Path
import os

TASK_LIMIT = 100
FILE_LIMIT = 100


def main():
    args = parse_args()
    config = read_config(
        config_path=args.config_path,
        config=args.config_name
    )

    data_dir = Path(config.get("data_dir"))
    log_dir = Path(config.get("log_dir"))
    main_task_name = data_dir.name
    assert data_dir.exists()

    bos_client = BOSClient(
        config_path=args.config_path,
        config_name=args.config_name,
    )

    remote_sub_tasks = bos_client.list_remote_sub_tasks(main_task_name)
    # 在本地先建目录，保持与 upload 时一致
    sub_dirs = [(data_dir / "batch_api" / name) for name in remote_sub_tasks]

    for sub_dir in sub_dirs:
        download_dir = sub_dir / "download"
        os.makedirs(download_dir, exist_ok=True)
        bos_client.download_batch_job(
            local_dir=download_dir,
            main_task_name=main_task_name,
            sub_task_name=sub_dir.name.replace("-", "_")
        )


if __name__ == "__main__":
    main()


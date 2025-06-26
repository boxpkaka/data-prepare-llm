from baidu.bos_client import BOSClient
from tools.batch_gen_request import parse_args
from utils.io import read_config
from pathlib import Path
import os
import re
import shutil
from loguru import logger
from datetime import datetime

def main():
    args = parse_args()
    config = read_config(
        config_path=args.config_path,
        config=args.config_name
    )
    log_dir = Path(config.get("log_dir"))
    logger.info(f"log dir {str(log_dir)}")
    assert log_dir.exists()
    data_dir = Path(config.get("data_dir"))
    assert data_dir.exists()
    current_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S") 
    log_path = log_dir / f"upload_dir_{data_dir.name}_{current_time}.log"
    logger.add(str(log_path), rotation="10 MB", level="INFO")
    logger.info(f"upload dir {str(data_dir)}")
    bos_client = BOSClient(
        config_path=args.config_path,
        config_name=args.config_name,
        inference_endpoint_name=""
    )

    bos_client.upload_dir(str(data_dir))


if __name__ == "__main__":
    main()
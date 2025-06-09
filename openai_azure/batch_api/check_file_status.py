from openai import AzureOpenAI
from safe_read_write import read_config

import argparse
import requests


def main(args):
    config = read_config(
        config_path=args.config_path,
        config=args.config
    )

    api_key=config.get("api_key")
    api_version=config.get("api_version")
    azure_endpoint=config.get("azure_endpoint")

    client = AzureOpenAI(
        api_key=api_key,
        api_version=api_version,
        azure_endpoint=azure_endpoint
    )

    # 使用批处理ID来检查批处理状态并获取错误信息
    batch_response = client.batches.retrieve(batch_id=args.batch_id)

    print("Batch failed. Retrieving error details:")
    # 打印 batch 的错误信息
    print(f"Error File ID: {batch_response.error_file_id}")
    print(f"Error details: {batch_response.errors}")
    
    file_id = batch_response.error_file_id
    
    file_response = client.files.content(file_id)
    error_content = file_response.read().decode('utf-8').strip()
    
    print("Error File Content:")
    for line in error_content.split('\n'):
        print(line)



if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--batch_id', help='ID of the error file to retrieve', type=str, required=True)
    parser.add_argument('--config_path',    help='',                           type=str)
    parser.add_argument('--config',         help='',                           type=str)
    args = parser.parse_args()
    
    main(args)

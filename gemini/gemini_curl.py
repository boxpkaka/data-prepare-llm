import requests
import argparse
from batch_api.safe_read_write import read_config


def main(config: dict):
    # 设置API密钥和请求的URL
    api_key = config.get("api_key")
    project_id = config.get("project_id")
    model_id = config.get("model_id")
    locations = config.get("locations")
    url = f"https://{locations}-aiplatform.googleapis.com/v1/projects/{project_id}/locations/{locations}/publishers/google/models/{model_id}:generateContent?key={api_key}"

    # 请求体
    data = {
        "contents": [
            {
                "role": "user",
                "parts": [
                    {"text": "Tell me a story about a magical backpack."}
                ]
            }
        ]
    }

    # 发送POST请求
    response = requests.post(url, json=data)

    # 打印响应
    print(response.json())
    
    
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config_path", help="", type=str)
    parser.add_argument("--config_name", help="", type=str)
    args = parser.parse_args()

    config = read_config(args.config_path, config=args.config_name)
    main(config)

import traceback

from loguru import logger
from openai import OpenAI

from utils.io import read_json


class LLMClient:
    def __init__(self, config_path: str, config_name: str) -> None:
        self.config = read_json(json_path=config_path).get(config_name)
        assert self.config

        self.client = None
        self.init_client()

    def init_client(self):
            self.client = OpenAI(
                api_key=self.config.get("api_key"), base_url=self.config.get("base_url")
            )

    def get_response(self, messages: list):
        try:
            response = self.client.chat.completions.create(
                model=self.config.get("model_name"), messages=messages
            )
            answer = response.choices[0].message.content
            return answer
        except Exception as e:
            logger.error(f"{e}")
            logger.error(traceback.format_exc())
            return None


if __name__ == "__main__":
    config_path = "/workspace/volume/data-skh/300-MT-Pro/workspace/data_prepare_gpt/bytedance/config/bytedance.json"
    config_name = "deepseek-v3"
    messages = [
        {"role": "system", "content": "You are a professional translator"},
        {
            "role": "user",
            "content": "Translate following Chinese to English:\n无论是深陷泥潭，还是徜徉云端，最终都要归于尘土，重要的不是起点与终点的差距，而是你在过程中如何与自己相遇。",
        },
    ]

    client = LLMClient(config_path=config_path, config_name=config_name)

    response = client.get_response(messages=messages)
    print(response)


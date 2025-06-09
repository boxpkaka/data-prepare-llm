import openai

from openai_azure.batch_api.safe_read_write import read_config


class AzureClient():
    def __init__(self, config_path: str, config_name: str) -> None:
        self.config = read_config(
            config_path=config_path,
            config=config_name
        )
        
        self.client = openai.AzureOpenAI(
            azure_endpoint="https://tlsm-gpt4o-test2.openai.azure.com/",
            api_key="2dd9bb411f6741f6bebfddb016a3698f",
            api_version="2024-07-01-preview",
        )
            
    @staticmethod
    def get_prompted_text(text_in: str, config: dict) -> str:
        NEED_LANG = config.get("need_language", "Chinese")
        PROMPT_PREFIX = config.get("prompt_prefix", "Translate")
        src_lang = config.get("src_language", "English")
        prompt_suffix = ': \n'.join(NEED_LANG) + ": "
        text = f"{PROMPT_PREFIX}\n\n{src_lang}: {text_in}\n{prompt_suffix}"
        return text.strip()


    def chat(self, prompt: str = None, process_prompt: bool = False, messages: list = None) -> dict:
        
        assert prompt or messages
        
        if process_prompt and prompt is not None:
            prompt = self.get_prompted_text(
                config=self.config,
                text_in=prompt
            )

        if messages is None:
            messages=[
                {"role": "user", "content": prompt},
            ]

        response = self.client.chat.completions.create(
            model="gpt-4o", # model = "deployment_name".
            messages=messages
        )

        return response


if __name__ == "__main__":
    pass


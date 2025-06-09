from deepseek.deepseek_client import DeepSeekClient


if __name__ == "__main__":
    config_path = "/workspace/volume/data-skh/300-MT-Pro/workspace/data_prepare_gpt/deepseek/config/chat.json"
    config_name = "volcengine-r1"

    client = DeepSeekClient(
        config_path=config_path,
        config_name=config_name
    )

    result = client.gen_field_sentences(
        language="zh-cn",
        num=50
    )
    print("\n".join(result))

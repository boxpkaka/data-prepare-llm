from bytedance.ptu.client import LLMClient
from bytedance.ptu.prompt import SST_PROMPT


def main():
    config_path = "/workspace/volume/data-skh/300-MT-Pro/workspace/data_prepare_gpt/bytedance/config/bytedance.json"
    config_name = "deepseek-v3"
    client = LLMClient(config_path=config_path, config_name=config_name)

    sentence = "因此我们在吃零食的时候，不妨多吃一些巧克力。顺便说一句，我每天都在吃，不过并非什么样的巧克力都合适，我们一定要选择可可成分在百分之七十以上的巧克力。当然了，尽管巧克力有益身体，但是由于其中含有糖分，因此不要过多食用，建议每天二十五克一点一点的吃，这样比较好。"
    messages = [
        {"role": "user", "content": SST_PROMPT},
        {"role": "user", "content": sentence},
    ]

    response = client.get_response(messages=messages)
    print(response)


if __name__ == "__main__":
    main()


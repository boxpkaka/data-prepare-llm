
from openai import OpenAI

client = OpenAI(
    api_key="bce-v3/ALTAK-bLs2ZJlXLA2TNdduv4xxz/8b45fe8c9ac3ba65d2ee9eaea2d4a117798af3c7",  # 千帆ModelBuilder平台bearer token
    base_url="https://qianfan.baidubce.com/v2",  # 千帆ModelBuilder平台域名
    # default_headers={"appid": "app-Mu***q6"}   # 千帆ModelBuilder平台应用ID，非必传
)

completion = client.chat.completions.create(
    model="deepseek-v3", # 预置服务请查看支持的模型列表
    messages=[{'role': 'system', 'content': 'You are a helpful assistant.'},
              {'role': 'user', 'content': 'Hello！'}]
)

print(completion.choices[0].message)

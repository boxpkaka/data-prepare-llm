# Please install OpenAI SDK first: `pip3 install openai`
from openai import OpenAI
from utils.io import read_config
from utils.prompt import SST_PROMPT

from utils.topic import TOPIC, TOPIC_PROMPT
from tools import ISO_MAP

import random


class DeepSeekClient():
    def __init__(self, config_path: str, config_name: str) -> None:
        self.config = read_config(config_path=config_path, config=config_name)
        self.client = None
        
        self.init_client()
    
    def init_client(self):
        self.client = OpenAI(
            api_key=self.config.get("api_key"), 
            base_url=self.config.get("base_url")
            )

    def chat(self, messages: list):
        response = self.client.chat.completions.create(
            model=self.config.get("model_name"),
            messages=messages
        )
        content = response.choices[0].message.content
        return content

    def get_all_topic_prompts(
        self, 
        topic_dict: dict = TOPIC, 
        jointer: str = '-',
        num: int = 10,
        language: str = "zh-cn"
    ) -> list[tuple[str, str]]:
        topics: list[str] = []

        def dfs(node, path: list[str]):
            # dict ⇒ 深入 value；键本身算入路径
            if isinstance(node, dict):
                for k, v in node.items():
                    dfs(v, path + [k])
            # list ⇒ 只深入元素；索引不算字符串，可跳过
            elif isinstance(node, list):
                for item in node:
                    dfs(item, path)
            # 基本类型
            else:
                # 节点自身是字符串要计入；非字符串 (int/float/bool/None) 则忽略
                extra = [node] if isinstance(node, str) else []
                # 过滤掉非 str 的 path 片段（理论上 path 内全是 str）
                tokens = [p for p in path if isinstance(p, str)] + extra
                if tokens:                              # 至少含一个字符串
                    topics.append(jointer.join(tokens))

        dfs(topic_dict, [])
        prompts = []
        for topic in topics:
            prompt = TOPIC_PROMPT.replace("[num]", str(num))
            prompt = prompt.replace("[topic]", f"[{topic}]")
            prompt = prompt.replace("[language]", ISO_MAP[language]["chinese"])
            prompts.append((prompt, topic))
        return prompts

    def gen_field_sentences(self, language: str, num: int) -> list:
        prompts = self.get_all_topic_prompts(num=num, language=language)
        prompt, topic = random.choice(prompts)
        print(topic)
        response = self.chat(
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        res = response.split("\n")
        return res

    def get_sst_data(self, sentence: str) -> str:
        response = self.chat(
            messages=[
                {"role": "user", "content": SST_PROMPT},
                {"role": "user", "content": sentence}
            ]
        )
        content = response.choices[0].message.content
        return content

if __name__ == "__main__":
    messages = [{"role":"user","content":"围绕[节日祝福\/邀请-礼物与回礼-环保礼物]这一场景，生成50条中文句子。\n写作要求\n1. 角色多元：对白可来自不同身份、立场或情绪（如主持人\/参与者\/路人\/吐槽者\/发问者等），避免只有单一视角。\n2. 覆盖意图：请横向联想并尽量包含下列常见话语功能，每一功能至少出现 1 句：\n   - 开场\/招呼 - 询问\/确认 - 建议\/提醒 - 反馈\/回答 - 鼓励\/调侃 - 结束\/告别  \n   （如场景特殊，可替换、增删功能条目）\n3. 语言多样：  \n   - 句式（陈述\/祈使\/疑问\/感叹…）和标点（。！？…）要有变化；  \n   - 可随机加入“嗯、啊、欸、嗷、额、哈” 等口头语，**同一口头语在不同句中最多出现 2 次**；  \n   - 避免连续使用相同开头或高频短语。  \n4. 去重自检：生成完毕后，自行比对删除 **相似度 > 80%** 的句子并重写直至满足数量。\n5. 输出格式：**仅输出结果**，不要编号、引号或额外说明，各句用换行符分隔。"}]
    client = DeepSeekClient(
        config_path="/workspace/volume/data-skh/300-MT-Pro/workspace/data_prepare_gpt/deepseek/config/chat.json",
        config_name="tmk-v3"
    )
    response = client.chat(messages=messages)
    print(response)


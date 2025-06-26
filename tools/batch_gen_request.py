import os
import re
import traceback
import ujson
import argparse
from pathlib import Path
from multiprocessing import Pool, cpu_count
from loguru import logger
from utils.topic import TOPIC, TOPIC_PROMPT
from utils.prompt import SST_PROMPT
from tools import ISO_MAP

from utils.io import read_config
from tools import (
    DEFAULT_NEED_LANG,
    DEFAULT_STYLE,
    DEFAULT_SCENE,
    DEFAULT_PROMPT_PREFIX,
    DEFAULT_STYLE_SUFFIX,
    DEFAULT_SCENE_SUFFIX,
    DEFAULT_MAX_TOKENS,
)

CLIENT_TYPE = [
    "azure",
    "baidu"
]

TASK = {
    "norm":{
        "id_key":"utt",
        "content_key":"text",
    },
    "translation":{
        "id_key":"utt",
        "content_key":"text",
    },
    "sst":{},
    "topic":{},
}




class BatchRequestGenerator:
    def __init__(self, config: dict):
        self.data_dir = config.get("data_dir", "")
        self.model_name = config.get("model_name")
        self.prompt_prefix = config.get("prompt_prefix", DEFAULT_PROMPT_PREFIX)
        self.need_lang = config.get("need_language", DEFAULT_NEED_LANG)
        self.style = config.get("style", DEFAULT_STYLE)
        self.scene = config.get("scene", DEFAULT_SCENE)
        self.style_suffix = config.get("style_suffix", DEFAULT_STYLE_SUFFIX)
        self.scene_suffix = config.get("scene_suffix", DEFAULT_SCENE_SUFFIX)
        self.src_lang = config.get("src_lang", "en")
        self.max_tokens = config.get("max_tokens", DEFAULT_MAX_TOKENS)
        self.prompt = config.get("prompt", None)

        self.client_type = config.get("client_type", "openai")
        self.task = config.get("task", "norm")
        self.target_num = config.get("target_num", 10)
        self.id_key = config.get("id_key", TASK[self.task]["id_key"])
        self.content_key = config.get("content_key", TASK[self.task]["content_key"])

        assert self.client_type in CLIENT_TYPE
        assert self.task in TASK

    def chunk(self, in_list: list, size: int = 1000) -> list[list]:
        return [in_list[i:i + size] for i in range(0, len(in_list), size)]

    def get_all_topic_prompts(self, topic_dict: dict = TOPIC, jointer: str = '-') -> list[tuple[str, str]]:
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
            prompt = TOPIC_PROMPT.replace("[num]", str(self.target_num))
            prompt = prompt.replace("[topic]", f"[{topic}]")
            prompt = prompt.replace("[language]", ISO_MAP[self.src_lang]["chinese"])
            prompts.append((prompt, topic))
        return prompts

    def get_prompted_text(self, text_in: str) -> str:
        if self.prompt:
            return f"{self.prompt}\n{text_in}"

        prompt_suffix = ": \n".join(self.need_lang) + ": " if self.need_lang else ""
        src_lang_en = ISO_MAP[self.src_lang]["english"]
        prompt_prefix = self.prompt_prefix.replace("[src_lang]", src_lang_en)

        text = (
            f"{prompt_prefix}\n\n"
            f"{src_lang_en}: {text_in}\n"
            f"{prompt_suffix}\n"
            f"{self.style_suffix}\n"
            f"{self.scene_suffix}"
        )
        return text.strip()

    def convert_prompt(self, origin: str) -> str:
        sentence = origin.split("English: ")[-1].split("Chinese: ")[0].strip()
        return self.get_prompted_text(sentence)

    def get_batch_request(
        self, 
        user_prompt: str | list[str], 
        custom_id: str,
        system_prompt: str = "You are a professional translator",
        ) -> dict:
        if system_prompt is None:
            messages = []
        else:
            messages = [{"role": "system", "content": system_prompt}]
        if isinstance(user_prompt, list):
            for _user_prompt in user_prompt:
                messages.append({"role": "user", "content": _user_prompt})
        else:
            messages.append({"role": "user", "content": user_prompt})

        if self.client_type == "openai":
            request = {
                "custom_id": custom_id,
                "method": "POST",
                "url": "/chat/completions",
                "body": {
                    "model": self.model_name,
                    "messages": messages,
                    "max_tokens": self.max_tokens,
                },
            }
        if self.client_type == "baidu":
            request = {
                "id": custom_id,
                "messages": messages
            }

        return request

    def process_line(self, line: str, file_path: Path) -> tuple[dict, str]:
        if self.task == "sst":
            item = ujson.loads(line)
            custom_id = item.get("wav_path")
            text = item.get(self.src_lang)
            request = self.get_batch_request(
                user_prompt=[SST_PROMPT, text],
                custom_id=custom_id,
                system_prompt=None
            )
        else:
            if file_path.suffix == ".jsonl":
                item = ujson.loads(line)
                custom_id = item.get(self.id_key)
                text = item.get(self.content_key)

            if file_path.suffix == ".list":
                try:
                    wav_path, text, *_ = re.split(r"\s+", line.strip(), maxsplit=1)
                except ValueError as e:
                    logger.warning(f"Line parse error: {line.strip()} - {e}")
                    return None, None
                custom_id = wav_path
            
            if self.task == "norm":
                request = self.get_batch_request(user_prompt=text, custom_id=custom_id, system_prompt=self.prompt)
            else:
                prompt_text = self.get_prompted_text(text)
                request = self.get_batch_request(user_prompt=prompt_text, custom_id=custom_id)

        return request, custom_id

    def process_file(self, file_path: Path, output_path: Path):
        custom_id_set = set()
        processed_count = 0
        try:
            with (
                open(file_path, "r", encoding="utf-8") as fin, 
                open(output_path, "w", encoding="utf-8") as fout
                ):
                for line in fin:
                    result, custom_id = self.process_line(line, file_path)
                    if result is None:
                        continue
                    if custom_id in custom_id_set:
                        logger.warning(f"Duplicate custom_id: {custom_id}")
                        continue
                    fout.write(ujson.dumps(result, ensure_ascii=False) + "\n")
                    processed_count += 1
                    custom_id_set.add(custom_id)
            logger.success(
                f"File {file_path.name} processed with {processed_count} items."
            )
        except Exception as e:
            logger.error(f"Error processing file {file_path.name}: {e}")
            logger.error(traceback.format_exc())

    def run_process_without_input(self, out_dir: str):
        os.makedirs(out_dir, exist_ok=True)
        data_name = Path(self.data_dir).name
        if self.task == "topic":
            prompts = self.chunk(
                in_list=self.get_all_topic_prompts()
            )
            for i, prompt_chunk in enumerate(prompts):
                out_path = Path(out_dir) / f"{data_name}_{i:04d}.jsonl"
                with open(out_path, 'w', encoding='utf-8') as fout:
                    for prompt, topic in prompt_chunk:
                        request = self.get_batch_request(
                            system_prompt=None,
                            user_prompt=prompt,
                            custom_id=topic
                        )
                        fout.write(ujson.dumps(request, ensure_ascii=False) + "\n")
                logger.success(out_path)
        else:
            raise NotImplementedError

    def run_process_with_input(self, in_dir: Path, out_dir: Path):
        file_names = os.listdir(in_dir)
        tasks = []
        for file_name in file_names:
            file_path = in_dir / file_name
            output_path = (out_dir / file_name).with_suffix(".jsonl")
            tasks.append((file_path, output_path))
        with Pool(processes=cpu_count()) as pool:
            pool.starmap(self.process_file, tasks)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config_path", type=str)
    parser.add_argument("--config_name", type=str)
    return parser.parse_args()


def main():
    args = parse_args()
    config = read_config(config_path=args.config_path, config=args.config_name)
    generator = BatchRequestGenerator(config)

    if config.get("client_type") == "baidu":
        root_dir = Path(config.get("data_dir"))
    else:
        root_dir = Path(config.get("data_dir")).parent.parent
    
    if config.get("task") == "topic":
        out_dir = root_dir / "batch_api"
        generator.run_process_without_input(out_dir=out_dir)
    else:
        in_dir = root_dir / "split"
        out_dir = root_dir / "batch_api"
        os.makedirs(out_dir, exist_ok=True)
        generator.run_process_with_input(in_dir=in_dir, out_dir=out_dir)


if __name__ == "__main__":
    main()

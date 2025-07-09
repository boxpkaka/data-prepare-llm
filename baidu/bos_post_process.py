import os
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
import re

import ujson
from loguru import logger

from openai_azure.batch_api.convert_to_parallel import response_to_dict
from tools.batch_gen_request import parse_args
from utils.io import read_config, read_json, write_json
from collections import Counter

TASK = [
    "norm",
    "translation",
    "sst",
    "topic",
    "extract"
]

class NormalizeTaskChecker:
    def __init__(self, text: str, normalizedText: str, lang: str):
        self.text = text
        self.normalizedText = normalizedText
        self.lang = lang

    def _is_all_uppercase(self, text: str) -> bool:
        """检查字符串是否全为大写（至少包含一个字母）"""
        return text.isupper() and any(c.isalpha() for c in text)

    def check(self):
        """新增全大写文本检测逻辑"""
        if self.lang == "en" and self._is_all_uppercase(self.normalizedText):
            return False
        
        if self.lang == 'zh-cn':
            punctuations  = '，。！？'
        elif self.lang == 'en':
            punctuations  = ',.?!\''
        else:
            raise ValueError("Unsupported language type. Use 'zh-cn' or 'en'.")
        text = self.text
        normalizedText = self.normalizedText
        if self.lang == 'en':
            text = text.lower()
            normalizedText = normalizedText.lower()
        for punc in punctuations:
            text = text.replace(punc, '')
            normalizedText = normalizedText.replace(punc, '')
        if text != normalizedText:
            return False
        return True

def process_file(in_path: Path, out_path: Path, task: str, src_lang: str) -> dict:
    """
    处理单个文件，并将处理结果写入指定的输出文件。
    该函数返回一个统计数据字典，后续由主进程统一汇总写入。
    """
    if task not in TASK:
        logger.error(f"Wrong task type: {task}")
        return None
    file_name = in_path.name
    send_tokens = 0
    receive_tokens = 0
    total_tokens = 0
    send_chars = 0
    receive_chars = 0
    lines = 0
    # 处理过程只写入当前任务对应的输出文件，避免写入冲突（每个进程写入不同的文件）
    with (
        open(in_path, "r", encoding="utf-8") as fin,
        open(out_path, "w", encoding="utf-8") as fout,
    ):
        for line in fin:
            item = ujson.loads(line)
            create_time_stamp = item["output"]["created"]
            answer = item["output"]["choices"][0]["message"]["content"]

            for message in item["messages"]:
                send_chars += len(message["content"])
            receive_chars += len(answer)

            send_tokens += item["output"]["usage"]["prompt_tokens"]
            receive_tokens += item["output"]["usage"]["completion_tokens"]
            total_tokens += item["output"]["usage"]["total_tokens"]
            lines += 1

            metadata = item["id"]

            if task == "translation":
                prompt = item["messages"][1]["content"]
                origin_item = response_to_dict(response=prompt)
                dump_item = response_to_dict(response=answer)
                found = False
                dump_item["wav_path"] = metadata
                for lang, text in origin_item.items():
                    if text:
                        dump_item[lang] = origin_item[lang]
                        found = True
                        break
                if not found:
                    logger.warning(f"Can't find origin text: {prompt}")
            elif task == "topic":
                dump_item = {"topic": metadata}
                dump_item["contents"] = [sentence.strip() for sentence in answer.split("\n") if sentence]
            elif task == "norm":
                prompt = item["messages"][1]["content"]
                original_text = prompt.split("\n", 1)[-1]
                # original_text = item["messages"][1]["content"]
                normalized_text = answer
                try:
                    checker = NormalizeTaskChecker(original_text, normalized_text, src_lang)
                    check_result = checker.check()
                    if check_result:
                        dump_item = {"utt": metadata}
                        dump_item["src"] = original_text
                        dump_item["text"] = normalized_text
                    else:
                        logger.warning(f"norm task is not valid, utt : {metadata}, src : {original_text}, text : {normalized_text}")
                        continue
                except ValueError as e:
                    logger.error(f"规范化失败: {e}")
                    continue
            elif task == "extract":
                def parse_json_manually(raw_str):
                    # 提取 zh-cn
                    en_tag = '", "en": "'
                    zh_tag = '{"zh-cn": "'
                    en_tag_pos = raw_str.find(en_tag)
                    zh_cn_str = raw_str[len(zh_tag):en_tag_pos]
                    en_str = raw_str[en_tag_pos + len(en_tag):len(raw_str)-2]
                    return {"zh-cn": zh_cn_str, "en": en_str}
                try:
                    prompt = item["messages"][1]["content"]
                    prompt_lines = [line.strip() for line in prompt.splitlines() if line.strip()]
                    last_line = prompt_lines[-1] if prompt_lines else None  # 处理全空情况
                    if last_line:
                        dump_item = parse_json_manually(last_line)
                        dump_item["wav_path"] = metadata
                        termJson = ujson.loads(answer)
                        if isinstance(termJson, dict):
                            dump_item["term"] = termJson["term"]
                        else:
                            dump_item["term"] = None
                except Exception  as e:
                    logger.error(f"处理失败: {e} id:{metadata} file:{file_name} prompt:{prompt} answer:{answer}")
                    continue
            else:
                logger.error(f"No support task: {task}")
                return None

            fout.write(ujson.dumps(dump_item, ensure_ascii=False) + "\n")

    statistic_item = {
        file_name: {
            "create_time": create_time_stamp,
            "send_tokens": send_tokens,
            "receive_tokens": receive_tokens,
            "total_tokens": total_tokens,
            "send_chars": send_chars,
            "receive_chars": receive_chars,
            "lines": lines,
        }
    }
    logger.success(file_name)
    return statistic_item


def main():
    args = parse_args()
    config = read_config(config_path=args.config_path, config=args.config_name)

    data_dir = Path(config.get("data_dir"))
    task = config.get("task")
    src_lang = config.get("src_lang")

    log_path = f"baidu/log/{data_dir.name}.json"

    out_dir = data_dir / "complete"
    os.makedirs(out_dir, exist_ok=True)

    completion_path = out_dir / "completion.json"
    completion_item = read_json(completion_path)

    log_item = read_json(log_path)
    need_process_paths = []

    # 筛选出待处理文件的下载路径
    for sub_task_name, items in log_item.items():
        for file_name, infos in items.items():
            if infos.get("status") != "downloaded":
                continue
            if completion_item.get(file_name) is not None:
                continue
            need_process_paths.append(infos.get("download_path"))

    all_statistic = {}
    # 利用多进程并行处理文件，避免各进程间写入同一个汇总文件的风险，
    # 最终在主进程中统一写入统计信息。
    with ProcessPoolExecutor() as executor:
        future_to_path = {
            executor.submit(
                process_file, Path(in_path), out_dir / Path(in_path).name, task, src_lang
            ): in_path
            for in_path in need_process_paths
        }
        for future in as_completed(future_to_path):
            result = future.result()
            if result is not None:
                all_statistic.update(result)
    write_json(json_path=completion_path, dump_item=all_statistic, overwrite=True)


if __name__ == "__main__":
    main()

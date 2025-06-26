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
    "topic"
]

class NormalizeTaskChecker:
    def __init__(self, text: str, normalizedText: str, lang: str):
        self.text = text
        self.normalizedText = normalizedText
        self.lang = lang
        self.threshold = self._calculate_threshold()

    #  基于文本长度的线性调整​​
    # ​​短文本​​（如<50字符）：提高阈值（如0.1），避免因少量噪声导致误判。
    # ​​长文本​​（如>500字符）：降低阈值（如0.01），因长文本中噪声分布更分散，需更严格过滤
    def _calculate_threshold(self):
        length = len(self.text)
        if length < 50:
            return 0.1
        elif length > 500:
            return 0.01
        else:
            return 0.05  # 默认值

    def _is_all_uppercase(self, text: str) -> bool:
        """检查字符串是否全为大写（至少包含一个字母）"""
        return text.isupper() and any(c.isalpha() for c in text)

    def normalize_punctuation(self, text, lang):
        """
        规范化标点符号，中文模式下额外保留英文字符和数字
        :param text: 输入文本
        :param lang: 语言类型 ('zh-cn' 中文, 'en' 英文)
        :return: 规范化后的文本
        """
        if lang == 'zh-cn':
            # 中文模式：保留汉字、英文、数字、中英文标点及空格
            pattern = r'[^\u4e00-\u9fa5a-zA-Z0-9，。？！,.?!\'\s]'  # 新增a-zA-Z0-9
        elif lang == 'en':
            # 英文模式：保留字母、数字、英文标点及空格
            pattern = r'[^a-zA-Z0-9,.?!\'\s]'  # 保持原逻辑
        else:
            raise ValueError("Unsupported language type. Use 'zh-cn' or 'en'.")
        
        cleaned = re.sub(pattern, ' ', text)  # 非法字符替换为空格
        return re.sub(r'\s+', ' ', cleaned.strip())  # 合并连续空格

    def count_non_punct_chars(self, text: str) -> Counter:
        """
        统计文本中的非标点字符（完全忽略所有标点符号）
        :param text: 输入文本
        :return: Counter对象统计字符频次
        """
        # 匹配所有非标点字符（包括字母、数字、空格及非标点符号的其他字符）
        chars = re.findall(r'[^\s\W_]', text, flags=re.UNICODE)  # \W匹配非字母数字，加_排除下划线
        if self.lang == 'en':
            chars = [char.lower() for char in chars]  # 英文统一转小写
        return Counter(chars)

    def compare_distributions(self, original, normalized, threshold):
        total_orig = sum(original.values()) or 1
        total_norm = sum(normalized.values()) or 1
        
        diff_percent = {}
        for char in set(original) | set(normalized):
            orig_pct = original.get(char, 0) / total_orig
            norm_pct = normalized.get(char, 0) / total_norm
            diff = abs(orig_pct - norm_pct)
            diff_percent[char] = diff
            if diff > threshold:
                return False, diff_percent
        return True, diff_percent

    def check(self):
        """新增全大写文本检测逻辑"""
        if self.lang == "en" and self._is_all_uppercase(self.normalizedText):
            return {
                'original_text': self.text,
                'normalized_text': self.normalizedText,
                'is_valid': False,
                'reason': 'Input text is all uppercase'
            }
        
        normalized = self.normalize_punctuation(self.normalizedText, self.lang)
        orig_counts = self.count_non_punct_chars(self.text)
        norm_counts = self.count_non_punct_chars(normalized)
        
        keep_data, diff_percent = self.compare_distributions(orig_counts, norm_counts, self.threshold)
        
        return {
            'original_text': self.text,
            'normalized_text': normalized,
            'original_counts': orig_counts,
            'normalized_counts': norm_counts,
            'is_valid': keep_data,
            'diff_percent': diff_percent,
            'reason': None if keep_data else '字符分布差异过大'
        }

    def print_results(self, result):
        """
        打印处理结果
        """
        
        # 全大写文本直接输出原因并终止
        if result['reason'] == 'Input text is all uppercase':
            print(f"\n警告: 数据丢弃 - {result['reason']}")
            return  # 提前返回，不打印后续内容

        print("\n=== 原始文本 ===")
        print(result['original_text'])
        
        print("\n=== 规范化后文本 ===")
        print(result['normalized_text'])

        print("\n=== 字符统计 ===")
        print("原始文本非标点字符分布:")
        for char, count in result['original_counts'].most_common():
            print(f"'{char}': {count}")
        
        print("\n处理后非标点字符分布:")
        for char, count in result['normalized_counts'].most_common():
            print(f"'{char}': {count}")
        
        print("\n=== 数据有效性检查 ===")
        if result['is_valid']:
            print("数据有效 - 字符分布差异在允许范围内")
            print("各字符差异百分比:")
            for char, diff in result['diff_percent'].items():
                print(f"'{char}': {diff:.2%}")
        else:
            print(f"警告: 数据丢弃 - {result['reason']}")
            print("超出阈值的字符差异:")
            for char, diff in result['diff_percent'].items():
                if diff > self.threshold:  # 与compare_distributions中的阈值一致
                    print(f"'{char}': {diff:.2%}")

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
                original_text = item["messages"][1]["content"]
                normalized_text = answer
                try:
                    checker = NormalizeTaskChecker(original_text, normalized_text, src_lang)
                    check_result = checker.check()
                    if check_result["is_valid"]:
                        dump_item = {"utt": metadata}
                        dump_item["src"] = original_text
                        dump_item["text"] = check_result["normalized_text"]
                    else:
                        checker.print_results(check_result)
                        continue
                except ValueError as e:
                    logger.error(f"规范化失败: {e}")
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

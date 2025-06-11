import os
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import ujson
from loguru import logger

from openai_azure.batch_api.convert_to_parallel import response_to_dict
from tools.batch_gen_request import parse_args
from utils.io import read_config, read_json, write_json

TASK = [
    "norm",
    "translation",
    "sst",
    "topic"
]

def process_file(in_path: Path, out_path: Path, task: str) -> dict:
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
                src = prompt.split("\n", 1)[-1]
                punt = answer
                # 根据原始文本长度动态调整阈值
                dynamic_threshold = max(10, len(src) * 0.1)  # 取10或文本长度10%的较大值
                if len(punt) - len(src) >= dynamic_threshold:
                    logger.warning(f"punt error : file_name:{file_name} wav_path:{metadata} src:{src} punt:{punt}")
                    continue
                dump_item = {"utt": metadata}
                dump_item["src"] = src
                dump_item["text"] = punt
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
                process_file, Path(in_path), out_dir / Path(in_path).name, task
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

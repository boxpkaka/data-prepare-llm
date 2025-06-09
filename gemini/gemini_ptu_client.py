import argparse
import os
import queue
import threading
import time
from datetime import datetime
from queue import Queue

# import google.auth
import google
import ujson
import vertexai
from google.auth.transport.requests import Request
from loguru import logger
from vertexai.generative_models import (
    GenerativeModel,
    HarmCategory,
    HarmBlockThreshold,
    Part,
    SafetySetting,
)

from prompt.gen_prompt import get_prompted_text
from prompt.resolve_prompt import response_to_dict
from utils import (
    check_json_files_exist,
    create_lock,
    read_config,
    remove_lock,
    write_json_file,
)

SCOPES = ["https://www.googleapis.com/auth/cloud-platform"]


class VertexaiClient(object):
    def __init__(
        self, 
        credentials_path: str,
        project_id: str, 
        model_id: str, 
        location: str,
        data_dir: str,
        thread: int
    ) -> None:
        # get credentials
        credentials, project = google.auth.load_credentials_from_file(
            credentials_path, scopes=SCOPES
        )
        credentials.refresh(Request())  # 刷新凭据确保其有效
        vertexai.init(project=project_id, location=location, credentials=credentials)
        
        # get model
        self.model = GenerativeModel(model_id)
        
        # init current worker info     
        self.worker_info = {
            "data_dir": data_dir,
            "file_name": None,
            "total_lines": None,
            "statistic": {
                "lines": 0,
                "send_chars": 0,
                "receive_chars": 0,
                "total_tokens": 0, 
                "send_tokens": 0, 
                "receive_tokens": 0
            }
        }
        
        # others
        self.input_queue = Queue()
        self.output_queue = Queue()
        self.thread = thread
    
    
def get_model(
        credentials_path: str,
        project_id: str, 
        model_id: str, 
        location: str,
        ):
    credentials, project = google.auth.load_credentials_from_file(
    credentials_path, scopes=SCOPES
    )
    credentials.refresh(Request())  # 刷新凭据确保其有效
    vertexai.init(project=project_id, location=location, credentials=credentials)

    safety_config = [
        SafetySetting(
            category=HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
            threshold=HarmBlockThreshold.BLOCK_ONLY_HIGH,
        ),
        SafetySetting(
            category=HarmCategory.HARM_CATEGORY_HARASSMENT,
            threshold=HarmBlockThreshold.BLOCK_ONLY_HIGH,
        ),
        SafetySetting(
            category=HarmCategory.HARM_CATEGORY_UNSPECIFIED,
            threshold=HarmBlockThreshold.BLOCK_ONLY_HIGH,
        ),
        SafetySetting(
            category=HarmCategory.HARM_CATEGORY_HATE_SPEECH,
            threshold=HarmBlockThreshold.BLOCK_ONLY_HIGH,
        ),
        SafetySetting(
            category=HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
            threshold=HarmBlockThreshold.BLOCK_ONLY_HIGH,
        ),
    ]
    
    model = GenerativeModel(model_id, safety_settings=safety_config)
    
    return model
    
    
def prompt_to_raw(prompt: str) -> str:
    tmp = prompt.split("English: ", 2)[-1]
    tmp = tmp.split('\n')[0]
    return tmp.strip()
    
    
def generate_content(model, contents: str) -> dict:
    response = model.generate_content(contents=contents)
    return response

    
def process_response(worker_info: dict, response: str, text: str = None) -> dict | None:
    try:
        dump_dict = response_to_dict(response.text)
    except ValueError as e:
        if "safety filters" in str(e):
            logger.error(f"Safety block: {text}")
            return None
        else:
            logger.error(e)
            return None
    except Exception as e:
        logger.error(e)
        return None
        
    worker_info["statistic"]["lines"] += 1
    worker_info["statistic"]["send_chars"] += len(text)
    worker_info["statistic"]["receive_chars"] += len(response.text)
    worker_info["statistic"]["total_tokens"] += response.usage_metadata.total_token_count
    worker_info["statistic"]["send_tokens"] += response.usage_metadata.prompt_token_count
    worker_info["statistic"]["receive_tokens"] += (
        response.usage_metadata.candidates_token_count
    )
    return dump_dict


def fetch_response(model, output_queue, worker_info: dict, text: str) -> None:
    prompted_text = get_prompted_text(text)
    backoff_time = 0.3
    while True:
        try:
            response = generate_content(
                model=model, 
                contents=prompted_text
                )
            break
        except Exception as e:
            logger.warning(f"Rate limit hit: {e}. Retrying in {backoff_time} seconds...")
            time.sleep(backoff_time)
            backoff_time *= 2
            if backoff_time > 10:
                return
    
    dump_dict = process_response(
        worker_info=worker_info,
        response=response, 
        text=text)
    if dump_dict is None:
        return
    
    output_queue.put(dump_dict)
    
    cur_line = worker_info["statistic"].get("lines")
    total_lines = worker_info["total_lines"]
    if cur_line % 200 == 0 or cur_line == total_lines:
        logger.info(f"Processed {cur_line}/{total_lines} lines. ")
        logger.info(' | '.join([f"{key}: {value}" for key, value in worker_info["statistic"].items()]))
        
        
def worker(model, input_queue, output_queue, worker_info) -> None:
    while True:
        try:
            prompt = input_queue.get(timeout=1)  # 设置超时时间，防止阻塞
        except queue.Empty:
            logger.debug("No more tasks in the queue.")
            return
        
        if prompt is None:
            input_queue.task_done()
            return
        
        fetch_response(model, output_queue, worker_info, prompt)
        input_queue.task_done()
    
    
def get_need_process_file_names(worker_info: dict) -> tuple:
    data_dir = worker_info.get("data_dir")
    
    # init output folder and record file
    output_dir = os.path.join(data_dir, "gemini")
    completions = os.path.join(output_dir, "completions.json")
    
    # create output folder
    os.makedirs(output_dir, exist_ok=True)
    
    # check completion.json existing
    check_json_files_exist(completions)
    
    # read completions.json
    with open(completions, 'r', encoding='utf-8') as f:
        completion_infos = ujson.load(f)
        completed_file_names = set(completion_infos.keys())
    
    # list all jsonl file names in data dir
    file_names = set(
        [file_name for file_name in os.listdir(data_dir) 
            if file_name.endswith(".jsonl")]
        )
    
    locked_file_names  = set(
        [file_name[:-5] for file_name in os.listdir(data_dir) 
            if file_name.endswith(".lock")]
    )
    
    # get need process file_names
    need_process_file_names = file_names - completed_file_names - locked_file_names
    need_process_file_names = sorted(list(need_process_file_names))
    
    return need_process_file_names, output_dir, completions
    
    
def init_status(worker_info, file_path: str, input_queue) -> None:
    """
    init worker_info and input_queue

    Args:
        file_path (str): current file path
    """
    total_lines = 0
    with open(file_path, 'r', encoding='utf-8') as fin:
        for line in fin:
            item = ujson.loads(line)
            prompt = list(item.values())[0]
            text = prompt_to_raw(prompt)
            total_lines += 1
            input_queue.put(text)
            
    worker_info["file_name"] = os.path.basename(file_path)
    worker_info["total_lines"] = total_lines
    
    for k in worker_info["statistic"]:
        worker_info["statistic"][k] = 0
    
    
def process_results(self, save_path: str) -> None:
    with open(save_path, 'w', encoding='utf-8') as fout:
        while not self.all_work_done.is_set() or not self.output_queue.empty():
            try:
                result = self.output_queue.get(timeout=1)  # 增加超时时间
                if result:
                    ujson.dump(result, fout, ensure_ascii=False)
                    fout.write('\n')
                self.output_queue.task_done()
            except queue.Empty:
                continue
    
    
def start_request(
        credentials_path: str,
        project_id: str, 
        model_id: str, 
        location: str,
        data_dir: str, 
        thread: int
        ) -> None:
    
    model = get_model(
        credentials_path=credentials_path,
        project_id=project_id,
        model_id=model_id,
        location=location
    )
    print(model)
    # worker_info = {
    #     "data_dir": data_dir,
    #     "file_name": None,
    #     "total_lines": None,
    #     "statistic": {
    #         "lines": 0,
    #         "send_chars": 0,
    #         "receive_chars": 0,
    #         "total_tokens": 0, 
    #         "send_tokens": 0, 
    #         "receive_tokens": 0
    #     }
    # }
    # need_process_file_names, output_dir, completions = get_need_process_file_names(worker_info)
    
    # # init logger
    # time_now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    # logger_file = os.path.join('./log', f'Gemini-{time_now}.log')
    # logger.add(logger_file, level="DEBUG", rotation="500 MB")
    
    # for file_name in need_process_file_names:
    #     logger.info(f"start fetching: {file_name}")
    #     input_queue = Queue()
    #     output_queue = Queue()
    #     data_dir = worker_info.get("data_dir")
        
    #     file_path = os.path.join(data_dir, file_name)
    #     save_path = os.path.join(output_dir, file_name)
    #     logger.info(f"{file_path=}")
        
    #     # lock file
    #     lock_file = f"{file_path}.lock"
    #     create_lock(lock_file=lock_file)
    #     logger.info(f"create lock file: {lock_file}")
        
    #     try:
    #         # init
    #         init_status(worker_info, file_path, input_queue)
            
    #         logger.info(f"{thread=}")
    #         threads = []
    #         for _ in range(thread):
    #             t = threading.Thread(target=worker, args=(model, input_queue, output_queue, worker_info))
    #             t.start()
    #             threads.append(t)
            
    #         with open(save_path, 'w', encoding='utf-8') as fout:
    #             while True:
    #                 try:
    #                     result = output_queue.get(timeout=30)
    #                     if result:
    #                         ujson.dump(result, fout, ensure_ascii=False)
    #                         fout.write('\n')
    #                 except queue.Empty:
    #                     logger.error("Output queue get operation timed out.")
    #                     break
            
    #         input_queue.join()
    #         logger.debug("Processing completed. Sending stop signals to threads.")
    #         for _ in range(thread):
    #             input_queue.put(None)
            
    #         logger.debug("Waiting for threads to finish.")
    #         for t in threads:
    #             t.join()
                
    #         # post processing
    #         logger.success(f"{file_name}")
    #         logger.remove()
    #     except Exception as e:
    #         logger.error(f"file_name - {e}")
    #     finally:
    #         write_json_file(
    #             path=completions, 
    #             key=worker_info.get("file_name"), 
    #             value=worker_info.get("statistic")
    #         )
    #         remove_lock(lock_file)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config_path", help="", type=str)
    parser.add_argument("--config_name", help="", type=str)
    args = parser.parse_args()

    # 读取配置文件
    config = read_config(args.config_path, config=args.config_name)

    # 初始化 Vertex AI 客户端
    start_request(
        credentials_path=config.get("credentials_path"),  # 传入凭据文件路径
        project_id=config.get("project_id"),
        model_id=config.get("model_id"),
        location=config.get("location"),
        data_dir=config.get("data_dir"),
        thread=config.get("thread"),
    )


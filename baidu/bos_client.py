import os
from pathlib import Path
from datetime import datetime
from baidubce.auth.bce_credentials import BceCredentials
from baidubce.auth.bce_v1_signer import sign
from baidubce.bce_client_configuration import BceClientConfiguration
from baidubce.exception import BceError
from baidubce.services.bos.bos_client import BosClient
from loguru import logger
from qianfan import resources
from concurrent.futures import ThreadPoolExecutor, as_completed

from utils.io import read_config, write_json, read_json


class BOSClient():
    def __init__(self, config_path: str, config_name: str, inference_endpoint_name: str = None) -> None:
        config = read_config(
            config_path=config_path,
            config=config_name,
        )

        self.access_key_id = config.get("access_key_id")
        self.secret_access_key = config.get("secret_access_key")
        self.bos_endpoint = config.get("bos_endpoint")
        if inference_endpoint_name:
            self.inference_endpoint = config.get("inference_endpoint", {}).get(inference_endpoint_name)
        else:
            self.inference_endpoint = config.get("inference_endpoint")
        self.bucket_name = config.get("bucket_name")
        self.inference_params = config.get("inference_params")

        credentials = BceCredentials(
            access_key_id=self.access_key_id,
            secret_access_key=self.secret_access_key
        )

        # 创建配置
        config = BceClientConfiguration(
            credentials=credentials,
            endpoint=self.bos_endpoint
        )

        # 初始化 BOS 客户端
        self.client = BosClient(config)
        self.log_dir = Path("./baidu/log")
    def list_buckets(self) -> None:
        try:
            response = self.client.list_buckets()
            logger.success(f"Buckets: {response}")
        except Exception as e:
            logger.error(e)

    def create_bucket(self) -> None:
        try:
            self.create_bucket(self.bucket_name)
            print(f"Bucket '{self.bucket_name}' created!")
        except BceError as e:
            print(f"Error creating bucket: {e}")

    def upload_file(self, target_path: str, file_path: str, overwrite: bool = False) -> bool:
        file_path = str(file_path)
        target_path = str(target_path)
        response = self.client.list_objects(
            bucket_name=self.bucket_name,
            prefix=target_path,
            max_keys=9999
        )
        # logger.info(f"response: {response}")
        skip_upload = False
        for item in response.contents:
            path = item.key
            if target_path == path:
                skip_upload = True
                break

        if skip_upload and not overwrite:
            logger.warning(f"Skip upload: {target_path}")
            return

        try:
            self.client.put_object_from_file(
                bucket=self.bucket_name,
                file_name=file_path,
                key=target_path
            )
            logger.success(f"Uploaded {file_path} to {self.bucket_name}")
            return True
        except Exception as e:
            logger.error(f"Upload failed, Bucket: {self.bucket_name} File: {file_path} Error: {e}")
            return False

    def upload_dir(self, local_dir: str, max_workers: int = 10) -> None:
        """
        递归上传目录及其所有子目录内容
        Args:
            local_dir: 要上传的本地目录路径
            max_workers: 最大并发线程数
        """
        assert Path(local_dir).is_dir(), f"Not a directory: {local_dir}"
        
        # 递归获取所有文件路径（包含子目录）
        file_paths = []
        for root, _, files in os.walk(local_dir):
            for file in files:
                if not file.startswith('.'):  # 跳过隐藏文件
                    file_paths.append(Path(root) / file)
        
        # 带异常处理的线程池
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(self.upload_file, target_path=path, file_path=path): path
                for path in file_paths
            }
            
            for future in as_completed(futures):
                path = futures[future]
                try:
                    future.result()
                    print(f"✓ Uploaded: {path}")  # 成功日志
                except Exception as e:
                    print(f"✗ Failed to upload {path}: {e}")

    def download_file(self, bos_path: str, local_path: str) -> None:
        try:
            self.client.get_object_to_file(
                bucket_name=self.bucket_name, 
                key=bos_path, 
                file_name=local_path
            )
            logger.success(f"File {bos_path} downloaded to {local_path}!")
        except BceError as e:
            logger.error(f"Download failed, Bucket: {self.bucket_name} Name: {bos_path} Error: {e}")

    def delete_file(self, target_path: str) -> None:
        try:
            self.client.delete_object(self.bucket_name, target_path)
            logger.success(f"File {target_path} deleted successfully!")
        except BceError as e:
            logger.error(f"Error deleting file, Bucket: {self.bucket_name} Name: {target_path} Error: {e}")

    def download_batch_job(
        self,
        local_dir: Path,
        main_task_name: str,
        sub_task_name: str
    ) -> None:
        assert local_dir.exists()
        log_path = self.log_dir / f"{main_task_name}.json"
        log_item = read_json(json_path=log_path)
        if not log_item:
            log_item = {sub_task_name: {}}
        if log_item.get(sub_task_name) is None:
            log_item[sub_task_name] = {}

        bos_root_dir = f"{main_task_name}/{sub_task_name}/"
        src_dir = f"{bos_root_dir}input/"

        response = self.client.list_objects(
            bucket_name=self.bucket_name,
            prefix=bos_root_dir,
            max_keys=9999
        )

        futures = []
        with ThreadPoolExecutor() as executor:
            for item in response.contents:
                path = item.key
                # 忽略 input 文件夹下的文件
                if f"{bos_root_dir}input" not in path:
                    file_name = path.split("/")[-1]
                    download_path = local_dir / file_name
                    if log_item[sub_task_name].get(file_name, {}).get("status", "") == "downloaded":
                        continue

                    # 提交下载任务
                    future = executor.submit(
                        self.download_file,
                        bos_path=str(path),
                        local_path=str(download_path)
                    )
                    futures.append((future, file_name, path, download_path))
                    # 先标记为 pending（可选）
                    log_item[sub_task_name][file_name] = {
                        "bos_src_path": f"{src_dir}{file_name}",
                        "bos_tgt_path": bos_root_dir,
                        "bos_processed_path": path,
                        "download_path": str(download_path),
                        "status": "pending",
                    }

            # 等待所有下载任务完成，并更新状态
            for future, file_name, path, download_path in futures:
                future.result()  # 若下载出错，这里会抛出异常
                log_item[sub_task_name][file_name]["status"] = "downloaded"

        write_json(
            json_path=log_path,
            dump_item=log_item,
            overwrite=True
        )


    def create_batch_job_bos(self, bos_src_dir: str, bos_tgt_dir: str, task_name: str) -> None:
        """
        创建批量推理任务
        :param bos_src_dir: 输入数据的 BOS 路径
        :param bos_tgt_dir: 输出数据的 BOS 路径
        :param task_name: 任务名称
        """
        os.environ["QIANFAN_ACCESS_KEY"] = self.access_key_id
        os.environ["QIANFAN_SECRET_KEY"] = self.secret_access_key

        resp = resources.console.utils.call_action(
            # 调用本文API，该参数值为固定值，无需修改；对应API调用文档-请求结构-请求地址的后缀
            "/v2/batchinference", 
            # 调用本文API，该参数值为固定值，无需修改；对应API调用文档-请求参数-Query参数的Action
            "CreateBatchInferenceTask", 
            # 请查看本文请求参数说明，根据实际使用选择参数；对应API调用文档-请求参数-Body参数
            {
                "name":task_name,
                "description":task_name,
                "endpoint":self.inference_endpoint,
                "inferenceParams":self.inference_params,
                "inputBosUri":f"bos:/{self.bucket_name}/{bos_src_dir}",
                "outputBosUri":f"bos:/{self.bucket_name}/{bos_tgt_dir}",
                "dataFormat":"role"
            }
        )
        # print(resp.body)

    def create_batch_job_local(
        self, 
        local_dir: str, 
        main_task_name: str, 
        sub_task_name: str,
        overwrite: bool = False
    ) -> None:
        assert local_dir.exists()
        log_path = self.log_dir / f"{main_task_name}.json"
        log_item = read_json(json_path=log_path)
        if not log_item:
            log_item = {sub_task_name: {}}
        
        if log_item.get(sub_task_name) is None:
            log_item[sub_task_name] = {}
        else:
            if log_item[sub_task_name]:
                logger.warning(f"Skip mission: {sub_task_name}")
                return
        
        file_paths = [Path(local_dir) / file_name for file_name in os.listdir(local_dir)]
        src_dir = f"{main_task_name}/{sub_task_name}/input/"
        tgt_dir = f"{main_task_name}/{sub_task_name}/"

        def upload_and_log(file_path: Path):
            file_name = file_path.name
            ret = self.upload_file(
                target_path=f"{src_dir}{file_name}",
                file_path=str(file_path),
                overwrite=overwrite
            )
            if ret:
                return file_name, {
                    "bos_src_path": f"{src_dir}{file_name}",
                    "bos_tgt_path": f"{tgt_dir}{file_name}",
                    "local_path": str(file_path),
                    "status": "uploaded"
                }
            else:
                return None, None

        with ThreadPoolExecutor() as executor:
            results = list(executor.map(upload_and_log, file_paths))
            for file_name, file_log in results:
                if file_name:
                    log_item[sub_task_name][file_name] = file_log

        self.create_batch_job_bos(
            bos_src_dir=src_dir,
            bos_tgt_dir=tgt_dir,
            task_name=sub_task_name
        )

        write_json(
            json_path=log_path,
            dump_item=log_item,
            overwrite=False
        )


if __name__ == "__main__":
    bos_client = BOSClient(
        config_path="/workspace/volume/data-skh/300-MT-Pro/workspace/data_prepare_gpt/baidu/config/access.json",
        config_name="timekettle",
        inference_endpoint_name="deepseek-v3"
    )
    bos_client.create_batch_job_local(
        local_dir="/workspace/volume/data-skh/300-MT-Pro/data/baidu_batch_api/test/test_250226/batch_api/test_250226",
        task_name="test_250314_5"
    )
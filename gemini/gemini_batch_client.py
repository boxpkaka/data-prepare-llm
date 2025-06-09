import argparse
import os

import google
import google.auth
import pandas as pd
import requests
import ujson
import json
from google.auth.transport.requests import Request
from google.cloud import bigquery
from google.oauth2 import service_account
from loguru import logger

from gemini.gemini_client import get_prompted_text, prompt_to_raw
from utils import read_config


SCOPES = [
        "https://www.googleapis.com/auth/bigquery",
        "https://www.googleapis.com/auth/cloud-platform"
    ]


class BigQueryClient:
    def __init__(
        self, 
        credentials_path: str, 
        project_id: str,
        dataset_id: str,
        model_id: str,
        location: str,
        data_dir: str
        ) -> None:
        
        self.credentials = self._get_credentials(credentials_path)
        self.token = self.credentials.token
        
        self.client = bigquery.Client(credentials=self.credentials, project=project_id)
        self.data_dir = data_dir
        self.location = location
        self.project_id = project_id
        self.dataset_id = dataset_id
        self.model_id = model_id
        
        self.out_dataset_id = f"{dataset_id}_batch_{model_id}"
        
        self.dataset_id = self.format_dataset_id(self.dataset_id)
        self.out_dataset_id = self.format_dataset_id(self.out_dataset_id)
        
        self.check_dataset_exist(self.dataset_id)
        self.check_dataset_exist(self.out_dataset_id)

    def _get_credentials(self, credentials_path):
        # 从服务账号凭证文件加载凭证
        credentials = service_account.Credentials.from_service_account_file(
            credentials_path,
            scopes=SCOPES
            )
        
        # 刷新凭证以确保访问令牌生成
        credentials.refresh(Request())
        
        # 授权存储对象查看权限（在初始化时就为服务账号设置权限）
        # gcloud_command = f"gcloud projects add-iam-policy-binding {self.project_id} --member='serviceAccount:{credentials.service_account_email}' --role='roles/storage.objectViewer'"
        # os.system(gcloud_command)
        
        return credentials
    
    
    def upload_dataframe(self, df, dataset_id, table_id):
        # 定义 BigQuery 表的 schema
        schema = [bigquery.SchemaField(column, "STRING") for column in df.columns]
        
        # 指定表引用
        table_ref = f"{self.client.project}.{dataset_id}.{table_id}"
        
        # 上传 DataFrame
        job = self.client.load_table_from_dataframe(df, table_ref, job_config=bigquery.LoadJobConfig(schema=schema))
        job.result()  # 等待任务完成
        print(f"数据已成功上传到 BigQuery 表 {table_ref}")


    def upload_string(self, table_id: str, text: str):
        tabel_column = "request"
        
        # 将字符串封装为 DataFrame
        df = pd.DataFrame([{tabel_column: text}])
        
        # 定义 BigQuery 表的 schema
        schema = [bigquery.SchemaField(tabel_column, "STRING")]
        
        # 指定表引用
        table_ref = f"{self.client.project}.{self.dataset_id}.{table_id}"
        
        # 上传 DataFrame
        job = self.client.load_table_from_dataframe(df, table_ref, job_config=bigquery.LoadJobConfig(schema=schema))
        job.result()  # 等待任务完成
        print(f"数据已成功上传到 BigQuery 表 {table_ref}")
    
    
    def upload_json(self, table_id: str, json_data: dict):
        tabel_column = "request"
        
        # 将字典封装为 JSON 字符串
        json_string = json.dumps(json_data, ensure_ascii=False)
        
        # 封装为 DataFrame
        df = pd.DataFrame([{tabel_column: json_string}])
        
        # 定义 BigQuery 表的 schema，使用 "STRING" 类型
        schema = [bigquery.SchemaField(tabel_column, "STRING")]
        
        # 指定表引用
        table_ref = f"{self.client.project}.{self.dataset_id}.{table_id}"
        
        # 上传 DataFrame 到 BigQuery
        job = self.client.load_table_from_dataframe(df, table_ref, job_config=bigquery.LoadJobConfig(schema=schema))
        job.result()  # 等待任务完成
        print(f"数据已成功上传到 BigQuery 表 {table_ref}")
    
        
    def download_to_dataframe(self, dataset_id, table_id):
        # 指定表引用
        table_ref = f"{self.client.project}.{dataset_id}.{table_id}"
        
        # 查询数据并返回 DataFrame
        query = f"SELECT * FROM `{table_ref}`"
        df = self.client.query(query).to_dataframe()
        return df
    
    def query_table(self, table_id: str, is_out_dataset: bool = False):
        dataset_id = self.out_dataset_id if is_out_dataset else self.dataset_id
        query = f"""
        SELECT * FROM `{self.project_id}.{dataset_id}.{table_id}`
        LIMIT 5
        """
        df = self.client.query(query).to_dataframe()

        print("前五行的数据: ")
        pd.set_option('display.max_colwidth', None)
        print(df.to_string(index=False))

    
    def list_tables(self) -> list:
        cloud_table_ids = []
        datasets = self.client.list_datasets()
        for dataset in datasets:
            logger.info(f"Dataset: {dataset}")
            tables = self.client.list_tables(dataset.dataset_id)
            for table in tables:
                logger.info(f"Table: {table.table_id}")
                cloud_table_ids.append(table.table_id)
        
        return cloud_table_ids
    
    
    @staticmethod
    def format_dataset_id(dataset_id: str) -> str:
        new_dataset_id = dataset_id.replace("-", "_").replace(".", "_")
        return new_dataset_id
    
    
    @staticmethod
    def get_table_id_from_file_name(file_name: str) -> str:
        """
        remove ".json" and ".jsonl", change "." -> ""
        """
        table_id = file_name.replace(".jsonl", "").replace(".json", "").replace(".", "-")
        return table_id
    
    
    def check_dataset_exist(self, dataset_id: str):
        dataset_ref = bigquery.DatasetReference(self.client.project, dataset_id)
        try:
            self.client.get_dataset(dataset_ref)  # 如果数据集存在，将不会发生任何事情
            logger.info(f"Dataset {dataset_id} already exists.")
            
        except google.api_core.exceptions.NotFound:
            logger.warning(f"Dataset {dataset_id} does not exist, creating now...")
            
            dataset = bigquery.Dataset(dataset_ref)
            dataset.location = self.location     # 根据需要指定区域
            
            self.client.create_dataset(dataset)
            logger.success(f"Dataset {dataset_id} created successfully.")
    
    
    def get_need_upload_file_infos(self) -> list:    
        incoming_file_names = [name for name in os.listdir(self.data_dir) if name.endswith(".jsonl")]
        cloud_table_ids = set(self.list_tables())
        
        need_upload_file_infos = []
        for file_path in incoming_file_names:
            file_name = os.path.basename(file_path)
            table_id = self.get_table_id_from_file_name(file_name)
            if table_id in cloud_table_ids:
                continue
            need_upload_file_infos.append({"path": file_path, "table_id": table_id})
        
        return need_upload_file_infos
    
    
    def upload_jsonl_data(self) -> None:
        self.check_dataset_exist(self.dataset_id)
        
        need_upload_file_infos = self.get_need_upload_file_infos()
        
        for infos in need_upload_file_infos:
            file_path = infos.get("path")
            table_id = infos.get("table_id")
            logger.info(f"processing {file_path}")

            prompts = []
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        prompt = list(ujson.loads(line).values())[0]
                    except ujson.JSONDecodeError as e:
                        logger.error(line)
                        break
                    text = prompt_to_raw(prompt)
                    prompted_text = get_prompted_text(text)
                    prompts.append({"prompt": prompted_text})

            df = pd.DataFrame(prompts)
            schema = [bigquery.SchemaField("prompt", "STRING")]
            
            table_ref = f"{self.client.project}.{self.dataset_id}.{table_id}"
            
            job = self.client.load_table_from_dataframe(df, table_ref, job_config=bigquery.LoadJobConfig(schema=schema))
            job.result()
            
            logger.success(f"Data is uploaded: {table_ref}")


    def create_single_job(self, table_id: str):
        # 构造请求的 URL
        url = f"https://{self.location}-aiplatform.googleapis.com/v1/projects/{self.project_id}/locations/{self.location}/batchPredictionJobs"
        input_uri = f"bq://{self.project_id}.{self.dataset_id}.{table_id}"
        output_uri = f"bq://{self.project_id}.{self.out_dataset_id}.{table_id}"
        
        # 请求头
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json; charset=utf-8"
        }
        
        # 请求体
        body = {
            "displayName": "test",
            "model": f"publishers/google/models/{self.model_id}",
            "inputConfig": {
                "instancesFormat": "bigquery",
                "bigquerySource": {
                    "inputUri": input_uri  # BigQuery 输入表的 URI
                }
            },
            "outputConfig": {
                "predictionsFormat": "bigquery",
                "bigqueryDestination": {
                    "outputUri": output_uri  # BigQuery 输出表的 URI
                }
            }
        }

        
        json_body = json.dumps(body, ensure_ascii=False, indent=4)
        print(json_body)
        response = requests.post(url, headers=headers, data=json_body)
        
        # 检查响应
        if response.status_code == 200:
            logger.success("Batch prediction job created successfully.")
            print(response.json())
        else:
            logger.error(f"{response.status_code}")
            print(response.text)

    
    def list_batch_jobs(self):
        url = f"https://{self.location}-aiplatform.googleapis.com/v1/projects/{self.project_id}/locations/{self.location}/batchPredictionJobs"
    
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
        
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            jobs = response.json().get('batchPredictionJobs', [])
            if not jobs:
                print("No batch prediction jobs found.")
            else:
                for job in jobs:
                    print(job)
        else:
            print(f"Error: {response.status_code}, {response.text}")
    

    def get_batch_prediction_job_info(self, job_id):
        url = f"https://{self.location}-aiplatform.googleapis.com/v1/projects/{self.project_id}/locations/{self.location}/batchPredictionJobs/{job_id}"
        
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
        
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            job_info = response.json()
            print("Job Information:")
            for k, v in job_info.items():
                print(f"{k}: {v}")
        else:
            print(f"Error: {response.status_code}, {response.text}")


    def start_monitor(self):
        pass


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config_path", help="", type=str)
    parser.add_argument("--config_name", help="", type=str)
    args = parser.parse_args()

    # 读取配置文件
    config = read_config(args.config_path, config=args.config_name)

    # 初始化 BigQuery 客户端
    bq_client = BigQueryClient(
        credentials_path=config.get("credentials_path"), 
        project_id=config.get("project_id"),
        location=config.get("location"),
        model_id=config.get("model_id"),
        data_dir=config.get("data_dir"),
        dataset_id=config.get("dataset_id")
        )

    # bq_client.list_tables()
    # bq_client.list_batch_jobs()
    # bq_client.query_table(table_id="test")
    # bq_client.get_batch_prediction_job_info(job_id="6940326714048249856")
    # bq_client.create_single_job(table_id="test-1020-json")
    bq_client.query_table(table_id="test-1020-json", is_out_dataset=True)
    # bq_client.upload_string(table_id="test-1020", text="Hello, can you help me translate the following sentence to English?\n我想去一次剧院，你可以陪我去吗？")
    # json_data = {
    #     "contents": [
    #         {
    #             "role": "user",
    #             "parts": [
    #                 {
    #                     "text": "Please translate the following sentence to English. sentence:我想去一次剧院，你可以陪我去吗？"
    #                 }
    #             ]
    #         }
    #     ]
    # }

    # bq_client.upload_json("test-1020-json", json_data)

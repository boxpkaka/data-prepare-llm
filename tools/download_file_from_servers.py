import time
import os
import paramiko
import hashlib
from loguru import logger
import argparse

# SFTP 连接类
class SFTPClient:
    def __init__(self, hostname, port, username, password):
        self.hostname = hostname
        self.port = port
        self.username = username
        self.password = password
        self.sftp = None
        self.connect()

    def connect(self):
        try:
            # 初始化 Transport 对象
            transport = paramiko.Transport((self.hostname, self.port))
            
            # 设置 banner 和认证超时时间
            transport.banner_timeout = 30.0  # SSH banner 超时时间
            transport.auth_timeout = 30.0    # 认证超时时间
            
            # 建立连接
            transport.connect(username=self.username, password=self.password)
            
            # 创建 SFTP 客户端
            self.sftp = paramiko.SFTPClient.from_transport(transport)
        except Exception as e:
            logger.error(f"Error connecting to SFTP: {e}")
            self.sftp = None


    def list_files(self, remote_folder, retries=3):
        if not self.sftp:
            logger.error("SFTP connection is not established.")
            return []
        
        attempt = 0
        while attempt < retries:
            try:
                return self.sftp.listdir(remote_folder)
            except Exception as e:
                logger.error(f"Error listing files: {e}")
                attempt += 1
                time.sleep(5)  # 重试前等待几秒
        return []


    def download_file(self, remote_path, local_path):
        if not self.sftp:
            logger.error("SFTP connection is not established.")
            return

        logger.info(f"Downloading file: {remote_path} -> {local_path}")
        try:
            self.sftp.get(remote_path, local_path)
            logger.success(f"File {remote_path} downloaded to {local_path}")
        except Exception as e:
            logger.error(f"Error downloading file: {e}")


    def compute_remote_sha256(self, remote_file_path):
        try:
            with self.sftp.file(remote_file_path, 'rb') as remote_file:
                hash_sha256 = hashlib.sha256()
                while True:
                    data = remote_file.read(4096)  # 每次读取 4KB 数据
                    if not data:
                        break
                    hash_sha256.update(data)
                return hash_sha256.hexdigest()
        except Exception as e:
            logger.error(f"Error computing remote SHA-256: {e}")
            return None

    def close(self):
        if self.sftp:
            self.sftp.close()
            
# 计算本地文件的 SHA-256
def compute_local_sha256(local_file_path):
    try:
        hash_sha256 = hashlib.sha256()
        with open(local_file_path, "rb") as local_file:
            while True:
                data = local_file.read(4096)  # 每次读取 4KB 数据
                if not data:
                    break
                hash_sha256.update(data)
        return hash_sha256.hexdigest()
    except Exception as e:
        logger.error(f"Error computing local SHA-256: {e}")
        return None

# 从文件中读取已完成的文件清单
def load_completed_files(completed_files_path):
    if os.path.exists(completed_files_path):
        with open(completed_files_path, 'r') as file:
            return set(file.read().splitlines())
    return set()

# 更新已完成的文件清单
def update_completed_files(completed_files_path, file_name):
    with open(completed_files_path, 'a') as file:
        file.write(file_name + '\n')

# 轮询并下载新增文件
def main(args):
    hostname = args.hostname
    port = args.port
    username = args.username
    password = args.password    
    remote_folder = args.remote_folder
    local_folder = args.local_folder
    interval = args.interval
    
    logger.info(f"Hostname: {hostname}")
    logger.info(f"remote folder: {remote_folder}")
    logger.info(f"local folder: {local_folder}")
    
    sftp_client = SFTPClient(hostname, port, username, password)
    logger.debug("sftp_client has been created. ")
    # 加载已完成文件清单
    completed_files_path = os.path.join(local_folder, 'completions.txt')
    completed_files = load_completed_files(completed_files_path)
    logger.debug("completed_files")
    try:
        while True:
            # 列出远程文件夹中的文件
            remote_files = sftp_client.list_files(remote_folder)
            logger.debug("list remote files")
            # 检查新增文件并下载
            for file_name in remote_files:
                if file_name not in completed_files:
                    remote_file_path = os.path.join(remote_folder, file_name)
                    local_file_path = os.path.join(local_folder, file_name)
                    
                    # 下载文件
                    sftp_client.download_file(remote_file_path, local_file_path)

                    # NOTE @MingdongYu: sha256校验太慢，暂不使用
                    # # 计算远端文件的 SHA-256
                    # remote_sha256 = sftp_client.compute_remote_sha256(remote_file_path)
                    # # 计算本地文件的 SHA-256
                    # local_sha256 = compute_local_sha256(local_file_path)
                    # if remote_sha256 and local_sha256:
                    #     if remote_sha256 == local_sha256:
                    #         logger.success(f"SHA-256 checksum match for {file_name}")
                    #         # 更新已完成的文件清单
                    #         update_completed_files(completed_files_path, file_name)
                    #         # 记录已下载的文件
                    #         completed_files.add(file_name)
                    #     else:
                    #         logger.error(f"SHA-256 checksum mismatch for {file_name}")
                    # else:
                    #     logger.error(f"Error in computing SHA-256 for {file_name}")
                    
                    # 更新已完成的文件清单
                    update_completed_files(completed_files_path, file_name)
                    # 记录已下载的文件
                    completed_files.add(file_name)

            # 等待下一轮轮询
            logger.info(f"wait {interval}s...")
            time.sleep(interval)
    except KeyboardInterrupt:
        logger.info("Polling stopped.")
    finally:
        sftp_client.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--remote_folder", help="", type=str)
    parser.add_argument("--local_folder", help="", type=str)
    parser.add_argument("--hostname", help="", type=str)
    parser.add_argument("--port", help="", type=int)
    parser.add_argument("--username", help="", type=str)
    parser.add_argument("--password", help="", type=str)
    parser.add_argument("--interval", help="", type=int)
    args = parser.parse_args()
    
    main(args)

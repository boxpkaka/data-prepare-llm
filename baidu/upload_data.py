from baidu.bos_client import BOSClient
from tools.batch_gen_request import parse_args
from utils.io import read_config
from pathlib import Path
import os
import concurrent.futures
from functools import partial
from itertools import islice
from loguru import logger
import tempfile

# 这个会枚举目录（最多2层）里面的_punc_train.list后缀文件，校验里面的音频路径是否存在，将存在的音频通过多线程上传到bos

class LargeFileProcessor:
    def __init__(self, bos_client, max_workers=8, batch_size=10000):
        self.bos_client = bos_client
        self.max_workers = max_workers
        self.batch_size = batch_size  # 每批处理的行数
    
    def process_line(self, line):
        """处理单行数据，返回(新路径, 文本)或None"""
        line = line.strip()
        if not line:
            return None
        
        parts = line.split(' ', 1)
        if len(parts) < 2:
            logger.warning(f"行格式错误: {line}")
            return None
        
        old_path, text = parts
        new_path = old_path.replace(
            '/nasStore',
            '/nasStore-23/000-TrainDataSets'
        )
        return (new_path, text)

    def upload_batch(self, batch):
        """上传一批文件"""
        success_count = 0
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # 使用偏函数固定bos_client参数
            upload_func = partial(self._upload_single_file, self.bos_client)
            futures = {
                executor.submit(upload_func, path): path
                for path, _ in batch if path is not None
            }
            
            for future in concurrent.futures.as_completed(futures):
                path = futures[future]
                try:
                    if future.result():
                        success_count += 1
                except Exception as e:
                    logger.error(f"上传失败 {path}: {str(e)}")
        return success_count

    @staticmethod
    def _upload_single_file(bos_client, file_path, overwrite: bool = False):
        """单个文件上传逻辑"""
        if not os.path.exists(file_path):
            logger.error(f"文件不存在: {file_path}")
            return False
        return bos_client.upload_file(file_path, file_path, overwrite)

    def process_large_file(self, file_path):
        """流式处理大文件"""
        logger.info(f"开始处理大文件: {file_path}")
        total_lines = 0
        valid_count = 0
        missing_count = 0
        
        # 临时文件用于存储有效条目
        with tempfile.NamedTemporaryFile(mode='w+', delete=False, encoding='utf-8') as tmp_file:
            tmp_path = tmp_file.name
            try:
                with open(file_path, 'r', encoding='utf-8') as src_file:
                    while True:
                        # 分批读取
                        batch = list(islice(src_file, self.batch_size))
                        if not batch:
                            break
                        
                        # 处理当前批次
                        processed = []
                        for line in batch:
                            result = self.process_line(line)
                            if result:
                                processed.append(result)
                        
                        # 并行上传当前批次
                        batch_valid = self.upload_batch(processed)
                        batch_missing = len(processed) - batch_valid
                        
                        # 统计和记录
                        total_lines += len(batch)
                        valid_count += batch_valid
                        missing_count += batch_missing
                        
                        # 写入有效的条目到临时文件
                        for path, text in processed:
                            if os.path.exists(path):  # 再次检查避免竞争条件
                                tmp_file.write(f"{path} {text}\n")
                        
                        # 进度报告
                        if total_lines % (self.batch_size * 10) == 0:
                            logger.info(
                                f"处理进度: 总行数={total_lines:,} | "
                                f"有效={valid_count:,} | 缺失={missing_count:,}"
                            )
                
                logger.info(
                    f"文件处理完成: 总行数={total_lines:,} | "
                    f"有效={valid_count:,} | 缺失={missing_count:,}"
                )
                
                # 生成最终列表文件
                output_path = os.path.join(
                    os.path.dirname(file_path),
                    f"new_{os.path.basename(file_path)}"
                )
                shutil.move(tmp_path, output_path)
                
                # 上传最终的列表文件
                if self._upload_single_file(self.bos_client, output_path, True):
                    os.remove(output_path)
                return True
                
            except Exception as e:
                logger.error(f"处理文件异常: {str(e)}")
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
                return False

def main():
    args = parse_args()
    config = read_config(
        config_path=args.config_path,
        config=args.config_name
    )
    
    # 初始化日志
    log_dir = Path(config.get("log_dir"))
    logger.info(f"日志目录: {log_dir}")
    assert log_dir.exists()
    
    data_dir = Path(config.get("data_dir"))
    assert data_dir.exists()
    
    log_path = log_dir / f"{data_dir.name}_parallel.log"
    logger.add(str(log_path), rotation="100 MB", level="INFO")
    
    # 初始化BOS客户端
    bos_client = BOSClient(
        config_path=args.config_path,
        config_name=args.config_name,
        inference_endpoint_name=""
    )
    
    # 创建处理器
    processor = LargeFileProcessor(
        bos_client=bos_client,
        max_workers=16,  # 根据实际情况调整
        batch_size=50000  # 每批处理5万行
    )
    
    # 遍历目录
    max_depth = 2
    base_depth = len(str(data_dir).split(os.sep))
    
    for root, dirs, files in os.walk(str(data_dir)):
        current_depth = len(root.split(os.sep))
        if current_depth - base_depth >= max_depth:
            del dirs[:]
        
        for file in files:
            if file.endswith('_punc_train.list'):
                file_path = os.path.join(root, file)
                processor.process_large_file(file_path)

if __name__ == "__main__":
    main()
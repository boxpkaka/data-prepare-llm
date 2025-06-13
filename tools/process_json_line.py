import json
from pathlib import Path

def transform_line(line: str) -> str:
    """
    处理单行数据：
    1. 校验必需字段是否存在
    2. 重命名字段
    3. 返回处理后的JSON字符串（无效数据返回None）
    """
    try:
        data = json.loads(line.strip())
        # 校验必需字段
        if not all(key in data for key in ["en", "zh-cn", "wav_path"]):
            return None
        
        # 重命名字段
        transformed = {
            "text": data["en"],
            "zh": data["zh-cn"],
            "id": data["wav_path"]
        }
        return json.dumps(transformed, ensure_ascii=False)
    except json.JSONDecodeError:
        return None

def process_file(input_path: Path, output_path: Path):
    """
    处理整个文件：
    1. 逐行读取输入文件
    2. 过滤并转换有效数据
    3. 写入输出文件
    """
    with (
        open(input_path, 'r', encoding='utf-8') as fin,
        open(output_path, 'w', encoding='utf-8') as fout
    ):
        for line in fin:
            transformed = transform_line(line)
            if transformed is not None:
                fout.write(transformed + '\n')

if __name__ == "__main__":
    input_file = Path("/workspace/volume/data-skh/luoyuanming/data/baidu_batch_api/mt_trans_en2zh_250611/concat/mt_trans_en2zh_250611.jsonl")  # 替换为你的输入文件路径
    output_file = Path("/workspace/volume/data-skh/luoyuanming/data/baidu_batch_api/mt_trans_en2zh_250611/concat/mt_trans_en2zh_250611_filter.jsonl")  # 替换为输出文件路径
    
    # 执行处理
    process_file(input_file, output_file)
    print(f"处理完成！结果已保存到 {output_file}")
import re
from loguru import logger
from pathlib import Path


def get_path_text_map(list_path: str | Path) -> dict:
    list_path = Path(list_path)
    path_text_map = {}
    
    with open(list_path, 'r', encoding='utf-8') as f:
        for line in f:
            try:
                wav_path, text, *_ = re.split(r'\s+', line.strip(), maxsplit=1)
            except ValueError as e:
                logger.warning(f"{line.strip()}: {e}")
                continue
        
            path_text_map[wav_path] = text
    
    return path_text_map


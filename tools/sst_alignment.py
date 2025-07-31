import re
import ujson
from pathlib import Path
from loguru import logger


extra_punc = set("，。,.!?！？；;:、 ")
punctuation_pattern = re.compile(r'[，。！？；：]')


def sst_alignment(raw_sst_data: str, timestamp: list) -> list:
    try:
        format_sst_data = answer2list(text=raw_sst_data)
    except Exception as e:
        logger.warning(f"Parsing SST data failed: {e}\n{raw_sst_data}")
        return None
    try:
        aligned_sst_data = timestamp_alignment(
            sst_segments=format_sst_data,
            char_timestamp=timestamp,
        )
        return aligned_sst_data
    except Exception as e:
        logger.error(f"{e}\n{format_sst_data}\n{timestamp}")
        return None

def get_timestamp_item(timestamp_path: str) -> tuple:
    try:
        with open(timestamp_path, 'r', encoding='utf-8') as f:
            item = ujson.load(f)
            timestamp_item: list = item["tiers"]["words"]["entries"]
            return timestamp_item
    except Exception as e:
        # logger.warning(f"{e} - {wav_path}")
        return None

def format_timestamp(timestamp_item: list, raw_path: str | Path, src_lang: str) -> dict:
        try:
            with open(raw_path, 'r', encoding='utf-8') as f:
                raw_text = f.read().strip()
        except Exception as e:
            logger.warning(f"Reading: {raw_path} - {e}")
            return None
        format_timestamp_item = {}
        if src_lang == "zh":
            format_timestamp_item["text"] = raw_text.replace(" ", "")
        else:
            format_timestamp_item["text"] = raw_text.strip()
        format_timestamp_item["timestamp"] = []

        idx = -1
        for item in timestamp_item:
            start_time_s = item[0]
            end_time_s = item[1]
            char = item[2]
            if punctuation_pattern.match(char):
                # 如果遇到标点，则将标点添加到上一个字符元素后面
                if idx >= 0:
                    timestamp_item[idx]["word"] += char
            else:
                # 非标点字符，对应 result 中下一个位置
                idx += 1
                format_timestamp_item["timestamp"].append(
                    {
                        "word": char,
                        "start_time": int(start_time_s * 1000),
                        "end_time": int(end_time_s * 1000)
                    }
                )
                # 如果 A 中非标点字符数量超过 C 的长度，就跳出以免越界
                if idx >= len(timestamp_item):
                    break
        return format_timestamp_item

def answer2list(text: str) -> list:
    text = text.replace("```json", "").replace("```", "")
    try:
        items = ujson.loads(text)
    except Exception as e:
        logger.warning(f"Parsing answer failed: {e}\n{text}")
        return []
    result = []
    for item in items:
        transcription = item["src"]
        translation = item["tgt"]
        if not transcription and not translation:
            break
        result.append({
            "transcription": transcription,
            "translation": translation,
        })
    return result

def _is_punc(ch: str) -> bool:
    """Unicode 类别以 'P' 开头的是标点。"""
    return unicodedata.category(ch).startswith('P')

def _strip(txt: str) -> str:
    """去掉所有标点和空白，并统一小写（对汉字无影响）。"""
    return "".join(
        ch.lower()
        for ch in txt
        if not ch.isspace() and not _is_punc(ch) and ch not in extra_punc
    )

def timestamp_alignment(sst_segments: list, char_timestamp: list) -> list:
    """兼容：汉字级时间戳 ↔ 英文段 / 单词级时间戳 ↔ 中文段"""
    sst_segments = [seg for seg in sst_segments if seg["transcription"].strip()]

    # ----------- 1. 构造 full_chars 与 char2tok 映射 -------------
    stripped_tokens, char2tok = [], []
    for tok_idx, entry in enumerate(char_timestamp):
        token = _strip(entry["word"])
        stripped_tokens.append(token)
        char2tok.extend([tok_idx] * len(token))       # 每个字符映射到所属 token
    full_chars = "".join(stripped_tokens)
    nt = len(char_timestamp)

    # ----------- 2. 逐段对齐 ------------------------------------
    last_char_pos = 0
    for seg_idx, seg in enumerate(sst_segments):
        target = _strip(seg["transcription"])
        if not target:            # 全是标点或 filler
            logger.warning(f"seg#{seg_idx} 『{seg['transcription']}』 strip 后为空，跳过对齐")
            seg["start_time"] = seg["end_time"] = None
            continue

        # 2.1 精确匹配
        pos = full_chars.find(target, last_char_pos)
        if pos >= 0:
            start_tok = char2tok[pos]
            end_tok   = char2tok[pos + len(target) - 1]
            seg["start_time"] = char_timestamp[start_tok]["start_time"]
            seg["end_time"]   = char_timestamp[end_tok]["end_time"]
            last_char_pos = pos + len(target)
            continue

        # 2.2 模糊匹配：左右各裁 1~2 字符
        found = False
        for cut in (1, 2):
            if len(target) <= cut:
                break
            for slice_ in (target[cut:], target[:-cut]):   # 去左 or 去右
                pos2 = full_chars.find(slice_, last_char_pos)
                if pos2 >= 0:
                    start_tok = char2tok[pos2]
                    end_tok   = char2tok[pos2 + len(slice_) - 1]
                    seg["start_time"] = char_timestamp[start_tok]["start_time"]
                    seg["end_time"]   = char_timestamp[end_tok]["end_time"]
                    last_char_pos = pos2 + len(slice_)
                    found = True
                    break
            if found:
                break
        if found:
            continue

        # 2.3 仍未匹配 → 兜底
        logger.warning(f"seg#{seg_idx} 『{seg['transcription']}』 无法定位，使用兜底时间")
        if last_char_pos < len(char2tok):
            fb_tok = char2tok[last_char_pos]
        else:
            fb_tok = nt - 1
        seg["start_time"] = char_timestamp[fb_tok]["start_time"]
        seg["end_time"]   = char_timestamp[-1]["end_time"]
        # 不推进 last_char_pos，避免连锁错位

    return sst_segments


if __name__ == "__main__":
    result = sst_alignment(
        raw_sst_data='[{"transcription": "你好", "translation": "Hello"}]',
        timestamp=[[0.0, 0.5, "你"], [0.5, 1.0, "好"]]
    )

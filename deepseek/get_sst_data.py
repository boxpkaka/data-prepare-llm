from deepseek.deepseek_client import DeepSeekClient
import re
import ujson
import string

def timestamp_alignment(self, sst_segments: list, char_timestamp: list):
    cur_start_index = 0
    cur_end_index = 0  # Start from the first character

    for i, sst_seg in enumerate(sst_segments):
        # Number of characters in the current transcription
        step = len(sst_seg["transcription"])

        # Get the start time from the timestamp of the first character in the segment
        if cur_start_index > len(char_timestamp) - 1:
            start_time = char_timestamp[-1]["start_time"]
        else:
            start_time = char_timestamp[cur_start_index]["start_time"]

        # Get the end time from the timestamp of the last character in the segment
        if (cur_start_index + step) > len(char_timestamp):
            end_time = char_timestamp[-1]["end_time"]
        else:
            end_time = char_timestamp[cur_start_index + step - 1]["end_time"]

        # Assign the times to the segment
        sst_segments[i]["start_time"] = start_time
        sst_segments[i]["end_time"] = end_time

        # Move the start and end index for the next segment
        cur_start_index += step
        cur_end_index += step

    return sst_segments


def answer2list(text: str) -> list:
    sst_pattern = (r"(?:- )?\[已累积的原文内容\]：(.*?)\n(?:- )?\[已口播译文\]：(.*?)(?:\n|$)")
    """
    - 解析同传增量翻译回答，并只记录每一步的增量部分，
    - 如果译文增量为空，则将当前原文增量追加到上一条记录的原文中。
    - 最终输出形如：
        [
            {
                "transcription": "现在呢",
                "translation": "Now,"
            },
            {
                "transcription": "我们就来到",
                "translation": " we have arrived at"
            },
            {
                "transcription": "了",
                "translation": ""
            },
            ...
        ]
    """
    matches = re.findall(sst_pattern, text, flags=re.DOTALL)
    pairs = [
        {"transcription": t.strip(), "translation": trans.strip()}
        for t, trans in matches
    ]

    reversed_pairs = pairs[::-1]
    correct_chain = []
    for pair in reversed_pairs:
        if not correct_chain:
            correct_chain.append(pair)
        else:
            if pair["translation"] in correct_chain[-1]["translation"]:
                correct_chain.append(pair)
    correct_chain.reverse()

    # 计算相邻记录的增量，若译文增量为空则合并到上一个记录
    result = []
    for i, pair in enumerate(correct_chain):
        if i == 0:
            result.append(pair.copy())
        else:
            prev = correct_chain[i - 1]
            curr = pair
            # 计算原文增量
            if curr["transcription"].startswith(prev["transcription"]):
                inc_transcription = curr["transcription"][
                    len(prev["transcription"]) :
                ]
            else:
                inc_transcription = curr["transcription"]
            # 计算译文增量
            if curr["translation"].startswith(prev["translation"]):
                inc_translation = curr["translation"][len(prev["translation"]) :]
            else:
                inc_translation = curr["translation"]
            # 如果译文增量为空，则将当前原文增量追加到上一个记录中
            if inc_translation == "":
                result[-1]["transcription"] += inc_transcription
            elif inc_translation in [",", ".", "。", "，"]:
                continue
            else:
                result.append(
                    {
                        "transcription": inc_transcription,
                        "translation": inc_translation,
                    }
                )

    print(ujson.dumps(result, ensure_ascii=False, indent=4))
    return result


if __name__ == "__main__":
    config_path = "/workspace/volume/data-skh/300-MT-Pro/workspace/data_prepare_gpt/deepseek/config/chat.json"
    config_name = "tmk-v3"

    client = DeepSeekClient(
        config_path=config_path,
        config_name=config_name
    )

    res = client.get_sst_data(
        sentence="那你看一下有什么话你在跟我说你看你那边就尽快吧它能不能做能做的话咱就就尽快去走这个流程对吧看你了因为今天不是十二号"
    )

    print(res)
    print(answer2list(res))
    # test_data = [
    #     {
    #         "transcription": "这个留学生的比例在二零一五年只有百分之十三",
    #         "translation": "The proportion of international students was only 13% in 2015,"
    #     },
    #     {
    #         "transcription": "，而二零二二年。",
    #         "translation": " and in 2022."
    #     }
    # ]
    

    
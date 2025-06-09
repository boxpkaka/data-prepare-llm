from typing import List
import json
import sys
import os

LIMIT_LEN=100
SPECIAL_CHAR="，。；;,.!！:："

''' 
split paragraph when it's logger than 200 tokens
'''
def cut_string(paragraph:str, limit_len: int, split_char: str) -> List:
    sentences = paragraph.split(split_char)
    result = []
    current_paragraph = ""
    for sentence in sentences:
        if sentence == "":
            continue
        if sentence[0] == "”":
            if result:
                result[-1] = result[-1] + "”"
            sentence = sentence[1:]
            if sentence == "":
                continue
        if sentence[-1] not in SPECIAL_CHAR:
            sentence = sentence + split_char
        if len(current_paragraph) + len(sentence) <= limit_len:
            current_paragraph += sentence
        else:
            result.append(current_paragraph.strip())
            current_paragraph = sentence
    if current_paragraph:
        result.append(current_paragraph.strip())
    return result

def prepare_corpus_from_jsonl(file_path: str, save_dir: str, limit_len:int) -> None:
    file_name = file_path.split('/')[-1].split('.')[0]
    save_path = os.path.join(save_dir, file_name)
    with open(save_path, 'w', encoding='utf-8') as fout:
        with open(file_path, 'r', encoding='utf-8') as fin:
            for line in fin:
                json_data = json.loads(line.strip())
                splited = json_data['text'].split('\n')
                for paragraph in splited:
                    if 0 <= len(paragraph) <=2:
                        continue
                    if len(paragraph) > limit_len:
                        sentences = cut_string(paragraph, limit_len, "。")
                        for sentence in sentences:
                            if sentence == "":
                                continue
                            if len(sentence) <= limit_len:
                                fout.write(sentence + '\n')
                            else:
                                phrases = cut_string(sentence, limit_len, "，")
                                for phrase in phrases:
                                    if phrase:
                                        fout.write(phrase + '\n')
                    else:
                        fout.write(paragraph.strip() + '\n')
                    
                    
if __name__ == "__main__":
    path = sys.argv[1]
    save_dir = sys.argv[2]
    prepare_corpus_from_jsonl(path, save_dir, LIMIT_LEN)
    
    
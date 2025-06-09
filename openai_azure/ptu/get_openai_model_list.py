from openai import OpenAI
from typing import Dict

import datetime


API_KEY = "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"

def _get_model_dict(api_key=API_KEY) -> Dict:
    client = OpenAI(api_key=api_key)
    models = client.models.list()
    model_dict = {}
    
    for item in models:
        model_name = item.id
        timestamp = item.created
        release_time = datetime.datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d')
        model_dict[model_name] = release_time
    
    return model_dict

def get_model_type_dict() -> None:
    model_dict = _get_model_dict()
    type_name_dict = {'chat': [],
                      'completions': []}
    name_type_dict = {}
    for name in model_dict:
        if 'gpt-3.5-turbo-instruct' in name:
            type_name_dict['completions'].append(name)
            continue
        if 'gpt-4' in name:
            type_name_dict['chat'].append(name)
        if 'gpt-3.5-turbo' in name:
            type_name_dict['chat'].append(name)
    
    for _type, _name_list in type_name_dict.items():
        for _name in _name_list:
            name_type_dict[_name] = _type
        
    return name_type_dict


if __name__ == "__main__":
    a = get_model_type_dict()
    print(a)
    
    
    
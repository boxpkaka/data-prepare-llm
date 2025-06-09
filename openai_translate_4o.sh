#!/bin/bash

data_path="/workspace/volume/data-skh/300-MT-Pro/data/modelbest-preview-test-100/zh/modelbase-preview-100.jsonl"
save_path="/workspace/volume/data-skh/300-MT-Pro/data/modelbest-preview-test-100/zh/translation"

src_lang="Chinese"
tgt_lang="English"

model_name="gpt-4o"
is_azure=true
api_key="2dd9bb411f6741f6bebfddb016a3698f"
api_version="2024-10-01-preview"
azure_end_point="https://tlsm-gpt4o-test2.openai.azure.com/"
max_token=500
thread=1

log_path=log/${model_name}$(date "+%Y-%m-%d-%H-%M-%S").log

param=''
if [ "$is_azure" = true ]; then
  param="--is_azure"
fi

# nohup \
python openai/ptu/translate_line.py \
  --data_path $data_path \
  --save_path $save_path \
  --api_key $api_key \
  --api_version $api_version \
  --azure_end_point $azure_end_point \
  --model_name $model_name \
  --max_token $max_token \
  --thread $thread \
  --src_lang $src_lang \
  --tgt_lang $tgt_lang \
  $param \
  # >$log_path 2>&1 &

# Model Name
# dall-e-3-3.0
# dall-e-2-2.0
# gpt-35-turbo-0301
# gpt-35-turbo-0613
# gpt-35-turbo-1106
# gpt-35-turbo-0125
# gpt-35-turbo-instruct-0914
# gpt-35-turbo-16k-0613
# gpt-4-0125-Preview
# gpt-4-1106-Preview
# gpt-4-0314
# gpt-4-0613
# gpt-4-32k-0314
# gpt-4-32k-0613
# gpt-4-vision-preview
# gpt-4-turbo-2024-04-09
# gpt-4-turbo-jp
# gpt-4o-2024-05-13
# ada
# text-similarity-ada-001
# text-search-ada-doc-001
# text-search-ada-query-001
# code-search-ada-code-001
# code-search-ada-text-001
# text-embedding-ada-002
# text-embedding-ada-002-2
# babbage
# text-similarity-babbage-001
# text-search-babbage-doc-001
# text-search-babbage-query-001
# code-search-babbage-code-001
# code-search-babbage-text-001
# curie
# text-similarity-curie-001
# text-search-curie-doc-001
# text-search-curie-query-001
# davinci
# text-similarity-davinci-001
# text-search-davinci-doc-001
# text-search-davinci-query-001
# text-embedding-3-small
# text-embedding-3-large
# dall-e-3
# dall-e-2
# gpt-35-turbo
# gpt-35-turbo-instruct
# gpt-35-turbo-16k
# gpt-4
# gpt-4-32k
# text-embedding-ada-002

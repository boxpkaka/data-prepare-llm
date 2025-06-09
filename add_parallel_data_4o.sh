#!/bin/bash

src_path=$1
tgt_dir=$2

model_name="tmk-gpt4o-ptu1"
is_azure=true
api_key="5eae26513ecd4963846168a7fd56721c"
api_version="2024-04-01-preview"
azure_end_point="https://tmk-gpt4o.openai.azure.com/"
max_token=2500
thread=1

src_name=$(echo $src_path | awk -F'/' '{print $NF}')
log_path=log/NEW-$src_name-$(date "+%Y-%m-%d").log

param=''
if [ "$is_azure" = true ]; then
  param="--is_azure"
fi

nohup \
python openai/ptu/add_parallel_data.py \
    --data_path $src_path \
    --save_dir $tgt_dir \
    --api_key $api_key \
    --api_version $api_version \
    --azure_end_point $azure_end_point \
    --model_name $model_name \
    --max_token $max_token \
    --thread $thread \
    $param \
    >$log_path 2>&1 &

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

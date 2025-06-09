#!/bin/bash

type=$1
index=$(printf "%04d" $2)

url=https://hf-mirror.com/datasets/Skywork/SkyPile-150B/resolve/main/data/2020-40_zh_${type}_${index}.jsonl?download=true
save_dir=/home/yumingdong/data/raw

name=$(basename $(echo $url | sed 's/\?download=true//'))
save_path=$save_dir/$name

wget -O $save_path $url

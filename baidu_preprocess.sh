#!/bin/bash

config_path=/workspace/volume/data-skh/300-MT-Pro/workspace/data_prepare_gpt/baidu/config/config-2506-k2asr-en-norm-250605.json
config_name="250605"
root_dir=/workspace/volume/data-skh/luoyuanming/data/baidu_batch_api/norm_punt_en_250605
num_split=1000

# Convert .raw to .split
if [[ -z "$root_dir" ]]; then
    echo "Skip file split"
else
    echo "split file..."
    bash tools/split_raw.sh $root_dir $num_split
fi

# Convert .split to .jsonl
bash batch_gen_request.sh $config_path $config_name


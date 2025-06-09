#!/bin/bash

config_path=baidu/config/config-2505-domain-zh-250501.json
config_name="250501"
root_dir=
num_split=100

# Convert .raw to .split
if [[ -v var && -z "$var" ]]; then
    echo "Skip file split"
else
    bash tools/split_raw.sh $root_dir $num_split
fi

# Convert .split to .jsonl
bash batch_gen_request.sh $config_path $config_name


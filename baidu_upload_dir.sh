#!/bin/bash

config_path=/workspace/volume/data-skh/300-MT-Pro/workspace/data-prepare-llm/baidu/config/config-2506-upload_dir_002-MultiTrainData-0626.json
config_name="1"

python -m baidu.upload_dir \
  --config_path $config_path \
  --config_name $config_name


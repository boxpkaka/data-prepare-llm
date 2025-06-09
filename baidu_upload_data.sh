#!/bin/bash

config_path=/home/luoyuanming/data_prepare_gpt/baidu/config/config-2506-asr-250609-upload-zh-001-ximalaya-train.json
config_name="250609"

python -m baidu.upload_data \
  --config_path $config_path \
  --config_name $config_name


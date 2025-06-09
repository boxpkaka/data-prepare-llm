#!/bin/bash

config_path=/workspace/volume/data-skh/300-MT-Pro/workspace/data_prepare_gpt/baidu/config/config-2506-k2asr-en-norm-250605.json
config_name="250605"

python -m baidu.bos_upload_create \
  --config_path $config_path \
  --config_name $config_name \


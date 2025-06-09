#!/bin/bash

config_path=/workspace/volume/data-skh/300-MT-Pro/workspace/data_prepare_gpt/baidu/config/config-2506-k2asr-zh-translation-250604.json
config_name="250604"

python -m baidu.bos_post_process \
  --config_path $config_path \
  --config_name $config_name \


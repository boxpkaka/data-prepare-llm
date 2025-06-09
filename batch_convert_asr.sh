#!/bin/bash

config_path=/workspace/volume/data-skh/300-MT-Pro/workspace/data_prepare_gpt/openai_azure/config/config-2411-asr-ko-tokenize.json

log_path=log/Convert-$(date "+%Y-%m-%d-%H-%M").log

# nohup \
python -m tmp.convert_asr_translation \
  --config_path $config_path \
  # >$log_path 2>&1 &

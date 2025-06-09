#!/bin/bash

config_path="/workspace/volume/data-skh/300-MT-Pro/workspace/data_prepare_gpt/gemini/config/gemini_config.json"
config_name="1"

log_path=log/Gemini-$config_name.log

if [ -f $log_path ]; then
    rm $log_path
fi

python -m gemini.gemini_ptu_client \
  --config_path $config_path \
  --config_name $config_name \


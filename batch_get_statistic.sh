#!/bin/bash

config_path=openai_azure/config/config-2412-asr-norm-zh-4omini-zonghe-1124.json

python openai_azure/batch_api/get_statistic.py\
  --config_path $config_path \

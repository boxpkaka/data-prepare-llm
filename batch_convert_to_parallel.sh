#!/bin/bash

config_path=openai_azure/config/config-2501-s2st-4o-translate-250122.json

log_path=log/Convert-$(date "+%Y-%m-%d-%H-%M").log

# nohup \
python -m openai_azure.batch_api.convert_to_parallel \
  --config_path $config_path \
  # >$log_path 2>&1 &

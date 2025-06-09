#!/bin/bash

config_path="openai_azure/config/config-asr-translation-672k.json"
config="test"
batch_id="batch_050c4ad0-8107-406b-aa34-4c4a8af0454b"

python openai_azure/batch_api/check_file_status.py \
  --config_path $config_path \
  --config $config \
  --batch_id $batch_id \

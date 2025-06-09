#!/bin/bash

config_path="/workspace/volume/data-skh/300-MT-Pro/workspace/data_prepare_gpt/openai/config/config-2409.json"
output_path="/workspace/volume/data-skh/300-MT-Pro/data/c4-60m-lang-44-test"

python openai/batch_api/concat_all_parallel.py \
  --config_path $config_path \
  --output_path $output_path

#!/bin/bash

config_path=$1
config_name=$2

# nohup \
python -m tools.batch_gen_request \
  --config_path $config_path \
  --config_name $config_name 

#!/bin/bash

config_path=openai_azure/config/config-2502-s2st-4o-translate-250212.json
config="23"
after_date="2025-02-12T11:20:00"

max_workers=4
max_inpro_val=10
upload=true
download=true

config_filename=$(basename "${config_path%.*}")
log_path=log/Monitor-$config_filename.log

if [ -f $log_path ]; then
    rm $log_path
fi

nohup \
python openai_azure/batch_api/batch_minitor.py \
  --config_path $config_path \
  --config $config \
  --max_workers $max_workers \
  --max_inpro_val $max_inpro_val \
  --after_date $after_date \
  ${upload:+--upload} \
  ${download:+--download} \
  >$log_path 2>&1 &

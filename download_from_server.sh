#!/bin/bash

remote_root_folder="/home/tkdata/300-MT-Pro/data/c4/batch-41-500/gpt"
local_root_folder="/workspace/volume/data-skh/300-MT-Pro/data/c4/en_batch_api/44-lang-style-scene/batch-41-500"
# data_dir="71"

hostname="62.210.125.123"
port=22
username="tkdata"
password="Beidazhiyu123"

interval=10

remote_folder="$remote_root_folder/gpt"
local_folder="$local_root_folder/gpt"
log_path=log/Download-$data_dir-$(date "+%Y-%m-%d-%H-%M").log

nohup \
python utils/download_file_from_servers.py \
  --remote_folder $remote_folder \
  --local_folder $local_folder \
  --hostname $hostname \
  --port $port \
  --username $username \
  --password $password \
  --interval $interval \
  >"$log_path" 2>&1 &
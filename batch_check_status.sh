#!/bin/bash
action=(
  "delete_failed"
  "cancel_processing"
  "write_unfailed"
  "check_status"
  "check_no_failed"
)

config_path="openai_azure/config/config-2502-s2st-norm-zh-4omini-250211.json"
config="31"

python openai_azure/batch_api/check_batch_status.py \
  --config_path "$config_path" \
  --config "$config" \
  --action "${action[3]}"


#!/bin/bash

python sequence_analyzer.py \
  --dataset dataset/AVPDiscover/AVP-external.csv \
  --output-path output/results/AVPDiscover/Ext \
  --min-seq-len 10 \
  --max-seq-len 100 \
  --batch-size 1000

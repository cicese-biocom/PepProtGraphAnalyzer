#!/bin/bash

python sequence_analyzer.py \
  --dataset dataset/AVPDiscover/AVPDiscover-test.csv \
  --output-path output/Paper_AVP/AVPDiscover/Test/ \
  --batch-size 1000

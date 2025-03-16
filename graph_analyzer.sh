#!/bin/bash

python graph_analyzer.py \
  --dataset datasets/AVPDiscover/AVPDiscover.csv \
  --output-path output/Test/ \
  --distance-intervals-json datasets/json/starpep_intervals.json \
  --graph-similarity-functions cosine_similarity graph_edit_distance \
  --ged-timeout 10 \
  --batch-size 1000
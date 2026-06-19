#!/bin/bash

echo ""

python graph_analyzer.py \
  --dataset dataset/AVPDiscover/AVP-external.csv \
  --output-path output/results/AVPDiscover/Ext \
  --distance-intervals-json dataset/json/starpep_intervals.json \
  --graph-similarity-functions cosine_similarity \
  --batch-size 1000 \
  --number-of-random-graphs 30 \
  --probability-edge-creation 0.5 \
  --max-seq-len 100
echo ""

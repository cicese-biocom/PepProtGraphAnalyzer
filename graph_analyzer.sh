#!/bin/bash

python graph_analyzer.py \
  --dataset dataset/AVPDiscover/AVPDiscover.csv \
  --output-path output/results/AVPDiscover/All \
  --distance-intervals-json dataset/json/starpep_intervals.json \
  --graph-similarity-functions cosine_similarity \
  --min-seq-len 10 \
  --max-seq-len 100 \
  --batch-size 1000 \
  --number-of-random-graphs 30 \
  --probability-edge-creation 0.5

python graph_analyzer.py \
  --dataset dataset/AVPDiscover/AVP-external.csv \
  --output-path output/results/AVPDiscover/Ext \
  --distance-intervals-json dataset/json/starpep_intervals.json \
  --graph-similarity-functions cosine_similarity \
  --min-seq-len 10 \
  --max-seq-len 100 \
  --batch-size 1000 \
  --number-of-random-graphs 30 \
  --probability-edge-creation 0.5

python graph_analyzer.py \
  --dataset dataset/AVPDiscover/AVPDiscover-train.csv \
  --output-path output/results/AVPDiscover/Train \
  --distance-intervals-json dataset/json/starpep_intervals.json \
  --graph-similarity-functions cosine_similarity \
  --min-seq-len 10 \
  --max-seq-len 100 \
  --batch-size 1000 \
  --number-of-random-graphs 30 \
  --probability-edge-creation 0.5

python graph_analyzer.py \
  --dataset dataset/AVPDiscover/AVPDiscover-val.csv \
  --output-path output/results/AVPDiscover/Val \
  --distance-intervals-json dataset/json/starpep_intervals.json \
  --graph-similarity-functions cosine_similarity \
  --min-seq-len 10 \
  --max-seq-len 100 \
  --batch-size 1000 \
  --number-of-random-graphs 30 \
  --probability-edge-creation 0.5

python graph_analyzer.py \
  --dataset dataset/AVPDiscover/AVPDiscover-test.csv \
  --output-path output/results/AVPDiscover/Test \
  --distance-intervals-json dataset/json/starpep_intervals.json \
  --graph-similarity-functions cosine_similarity \
  --min-seq-len 10 \
  --max-seq-len 100 \
  --batch-size 1000 \
  --number-of-random-graphs 30 \
  --probability-edge-creation 0.5

  python graph_analyzer.py \
  --dataset dataset/AVPDiscover/AVPDiscover.csv \
  --output-path output/results/AVPDiscover/All \
  --distance-intervals-json dataset/json/starpep_intervals.json \
  --graph-similarity-functions cosine_similarity \
  --min-seq-len 10 \
  --max-seq-len 100 \
  --batch-size 1000 \
  --number-of-random-graphs 30 \
  --probability-edge-creation 0.5
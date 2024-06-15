#!/bin/bash

dataset="datasets/AVPDiscover/AVP_External(reduced-not_in_AVPDiscover_10_to_100).csv"
pdb_path="datasets/AVPDiscover/ESMFold_pdbs (AVP_External)/"
tertiary_structure_method='esmfold'
amino_acid_representation="CA"
batch_size=56
distance_intervals_json_path='datasets/json/distance_intervals.json'
output_path='output/AVPDiscover/'

python graph_analyzer.py \
    --dataset "$dataset" \
    --pdb_path "$pdb_path" \
    --tertiary_structure_method="$tertiary_structure_method"  \
    --amino_acid_representation="$amino_acid_representation" \
    --batch_size="$batch_size" \
    --distance_intervals_json_path="$distance_intervals_json_path" \
    --output_path="$output_path"

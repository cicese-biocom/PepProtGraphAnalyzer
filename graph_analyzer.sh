#!/bin/bash

dataset="datasets/StarPep/StarPep.csv"
pdb_path="datasets/StarPep/ESMFold_pdbs/"
tertiary_structure_method='esmfold'
amino_acid_representation="CA"
batch_size=56
distance_intervals_json_path='datasets/json/distance_intervals.json'
output_path='output/StarPep/Paper/'

python graph_analyzer.py \
    --dataset "$dataset" \
    --pdb_path "$pdb_path" \
    --tertiary_structure_method="$tertiary_structure_method"  \
    --amino_acid_representation="$amino_acid_representation" \
    --batch_size="$batch_size" \
    --distance_intervals_json_path="$distance_intervals_json_path" \
    --output_path="$output_path"

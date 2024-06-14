#!/bin/bash

dataset="database/AVPDiscover/AVPDiscover.csv"
pdb_path="database/AVPDiscover/ESMFold_pdbs/"
tertiary_structure_method='esmfold'
amino_acid_representation="CA"
batch_size=56
output_path='output/AVPDiscover/Graph_Generation/'

python generate_graphs.py \
    --dataset "$dataset" \
    --pdb_path "$pdb_path" \
    --tertiary_structure_method="$tertiary_structure_method"  \
    --amino_acid_representation="$amino_acid_representation" \
    --batch_size="$batch_size" \
    --output_path="$output_path"

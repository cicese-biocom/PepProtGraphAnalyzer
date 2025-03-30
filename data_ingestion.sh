#!/bin/bash

dataset="datasets/StarPep/StarPep.csv"
pdb_path="datasets/StarPep/ESMFold_pdbs/"
tertiary_structure_method='esmfold'
output_path='output/StarPep/PaperNew/'
min_seq_len=10
max_seq_len=100

python data_ingestion.py \
    --dataset "$dataset" \
    --pdb-path "$pdb_path" \
    --tertiary-structure-method="$tertiary_structure_method" \
    --output-path="$output_path" \
    --min-sequence-len="$min_sequence_len" \
    --max-sequence-len="$max_sequence_len"
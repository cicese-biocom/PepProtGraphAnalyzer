#!/bin/bash

dataset="datasets/StarPep/StarPep.csv"
pdb_path="datasets/StarPep/ESMFold_pdbs/"
tertiary_structure_method='esmfold'
output_path='output/StarPep/PaperNew/'
minimum_sequence_length=10
maximum_sequence_length=100

python data_ingestion.py \
    --dataset "$dataset" \
    --pdb-path "$pdb_path" \
    --tertiary-structure-method="$tertiary_structure_method" \
    --output-path="$output_path" \
    --minimum-sequence-length="$minimum_sequence_length" \
    --maximum-sequence-length="$maximum_sequence_length"
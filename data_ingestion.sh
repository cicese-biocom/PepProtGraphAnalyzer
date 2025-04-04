#!/bin/bash

dataset="dataset/AVPDiscover/AVP-external.csv"
pdb_path="dataset/AVPDiscover/ESMFold_pdbs (AVP-external)/"
tertiary_structure_method='esmfold'
output_path='output/Paper_AVP/AVPDiscover/Ext/'

python data_ingestion.py \
    --dataset "$dataset" \
    --pdb-path "$pdb_path" \
    --tertiary-structure-method="$tertiary_structure_method" \
    --output-path="$output_path" \
    --predict-tertiary-structure
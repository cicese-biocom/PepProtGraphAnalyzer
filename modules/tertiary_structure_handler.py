import logging
import numpy as np
import pandas as pd
import torch
from pydantic import FilePath, DirectoryPath, BaseModel
from tqdm import tqdm
from modules import esmfold_model_handler as esmfold
from utils import pdb_parser, distances
from utils.distances import distance


def get_atom_coordinates_matrices(data: pd.DataFrame, parameters: BaseModel):
    # Get PDBs
    if parameters.predict_tertiary_structure:
        # Predict PDB
        pdbs = _predict_tertiary_structure(data, parameters.pdb_path)
    else:
        # Load PDBs
        pdbs = _load_tertiary_structure(data, parameters.pdb_path, parameters.output_paths['sequences_with_baseless_partitions_file'])

    # Get atom coordinate
    atom_coordinates_matrices = []
    for pdb_str in tqdm(pdbs, total=len(pdbs), desc="Getting coordinates matrix"):
        # Get atom coordinates from pdb
        coordinates_matrix = np.array(pdb_parser.get_atom_coordinates_from_pdb(pdb_str, parameters.amino_acid_representation),
                                      dtype='float64')
        
        # Translate to positive coordinates
        coordinates_matrix = np.array(distances.translate_to_positive_coordinates(coordinates_matrix), dtype='float64')

        # Save atom coordinates matrix
        atom_coordinates_matrices.append(coordinates_matrix)

    return atom_coordinates_matrices

    
def _load_tertiary_structure(data: pd.DataFrame, pdb_path: DirectoryPath, csv_file: FilePath):
    sequences_to_exclude = []
    pdbs = []
    try:
        for index, row in tqdm(data.iterrows(), total=len(data), desc="Loading pdb files"):
            pdb_file = pdb_path.joinpath(f"{row['id']}.pdb")
    
            pdb_str = pdb_parser.open_pdb(pdb_file)
            pdbs.append(pdb_str)
    except Exception as e:
        sequences_to_exclude = sequences_to_exclude.append(row)

    # Raise exception if sequences_to_exclude is not empty
    if sequences_to_exclude:
        sequences_to_exclude = pd.DataFrame(sequences_to_exclude)
        sequences_to_exclude.to_csv(csv_file, index=False)
        data = data.drop(sequences_to_exclude.index)

        # logging-ERROR
        logging.getLogger('logger'). \
            critical(f"Sequences not linked to PDB or with error when analyzing the PDB structure. See: {csv_file}")
        raise
    
    return pdbs


def _predict_tertiary_structure(data: pd.DataFrame, pdb_path: DirectoryPath):
    # Predict tertiary structures
    pdbs = esmfold.predict_structures(data)

    # Save PDBs
    pdb_names = [str(row.id) for (index, row) in data.iterrows()]
    for (pdb_name, pdb_str) in tqdm(zip(pdb_names, pdbs), total=len(pdbs), desc="Saving pdb files"):
        pdb_parser.save_pdb(pdb_str, pdb_name, pdb_path)

    #  logging-INFO
    logging.getLogger('logger'). \
        info(f"Predicted tertiary structures available in: {pdb_path}")

    return pdbs


def get_inter_amino_acid_distance(atom_coordinates, distance_functions):
    number_of_amino_acid = len(atom_coordinates)

    rows = []
    cols = []
    values = []
    for i in range(number_of_amino_acid):
        for j in range(i + 1, number_of_amino_acid):
            rows.append(i)
            cols.append(i)
            values.append(distance(atom_coordinates[i], atom_coordinates[j], distance_functions))

    edge_index = torch.tensor([rows, cols], dtype=torch.int64)
    edge_attr = torch.tensor(np.array(values), dtype=torch.float32)

    return edge_index, edge_attr

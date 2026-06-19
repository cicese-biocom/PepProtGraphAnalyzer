import logging
import numpy as np
import pandas as pd
from pydantic import FilePath, DirectoryPath
from tqdm import tqdm
from module import esmfold_model_handler as esmfold
from module.argument_parser import CommonArguments
from util import pdb_parser


def get_atom_coordinates_matrices(data: pd.DataFrame, parameters: CommonArguments):
    # Get PDBs
    if parameters.predict_tertiary_structure:
        # Predict PDB
        pdbs = _predict_tertiary_structure(data, parameters.pdb_path)
    else:
        # Load PDBs
        pdbs = _load_tertiary_structure(data, parameters.pdb_path, parameters.output_paths['non_pdb_bound_sequences_file'])

    # Get atom coordinate
    atom_coordinates_matrices = []
    for pdb_str in tqdm(pdbs, total=len(pdbs), desc="Getting coordinates matrix"):
        # Get atom coordinates from pdb
        coordinates_matrix = np.array(pdb_parser.get_atom_coordinates_from_pdb(pdb_str, parameters.amino_acid_representation),
                                      dtype='float64')
        
        # Translate to positive coordinates
        coordinates_matrix = np.array(translate_to_positive_coordinates(coordinates_matrix), dtype='float64')

        # Save atom coordinates matrix
        atom_coordinates_matrices.append(coordinates_matrix)

    return atom_coordinates_matrices


def _load_tertiary_structure(data: pd.DataFrame, pdb_path: DirectoryPath, csv_file: FilePath):
    sequences_to_exclude = []
    pdbs = []
    with tqdm(range(len(data)), total=len(data), desc="Loading pdb files", disable=False) as progress:
        for index, row in data.iterrows():
            try:
                pdb_file = pdb_path.joinpath(f"{row['id']}.pdb")

                pdb_str = pdb_parser.open_pdb(pdb_file)
                pdbs.append(pdb_str)
            except Exception as e:
                sequences_to_exclude.append(row)
            progress.update()

        if sequences_to_exclude:
            sequences_to_exclude_df = pd.DataFrame(sequences_to_exclude)
            sequences_to_exclude_df.to_csv(csv_file, index=False)
            logging.getLogger('logger').critical(
                f"Sequences not linked to PDB or with error when analyzing the PDB structure. See: {csv_file}")
            raise ValueError(
                f"Sequences not linked to PDB or with error when analyzing the PDB structure. See: {csv_file}")

        if len(pdbs) == 0:
            logging.getLogger('logger').critical(
                f"Sequences not linked to PDB or with error when analyzing the PDB structure. See: {csv_file}")
            raise ValueError(
                f"Sequences not linked to PDB or with error when analyzing the PDB structure. See: {csv_file}")

        return pdbs


def _predict_tertiary_structure(data: pd.DataFrame, pdb_path: DirectoryPath):
    # Predict tertiary structures
    pdbs = esmfold.predict_structures(data)

    # Save PDBs
    pdb_names = [str(row.id) for (index, row) in data.iterrows()]
    for (pdb_name, pdb_str) in tqdm(zip(pdb_names, pdbs), total=len(pdbs), desc="Saving pdb files"):
        pdb_parser.save_pdb(pdb_str, pdb_name, pdb_path)

    #  logging-INFO
    logging.getLogger('logger').info(f"Predicted tertiary structures available in: {pdb_path}")

    return pdbs


def translate_to_positive_coordinates(coordinates):
    min_x = min(min(coordinate[0] for coordinate in coordinates), 0)
    min_y = min(min(coordinate[1] for coordinate in coordinates), 0)
    min_z = min(min(coordinate[2] for coordinate in coordinates), 0)

    eps = 1e-6
    return [np.float64((coordinate[0] - min_x + eps, coordinate[1] - min_y + eps, coordinate[2] - min_z + eps)) for coordinate in coordinates]
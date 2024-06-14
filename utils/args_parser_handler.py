from argparse import ArgumentParser
from pathlib import Path
from typing import Dict


def set_of_distance_functions(value):
    functions = value.replace(" ", "").split(',')
    functions = set(functions)
    return functions


class ArgsParserHandler:
    def __init__(self):
        self.parser = ArgumentParser()

    def _add_common_arguments(self):
        self.parser.add_argument('--dataset', type=Path, required=False,
                                 help='Path to the input dataset in csv format')
        self.parser.add_argument('--predict_tertiary_structure', action="store_true",
                                 help='True if specified, otherwise, False. True indicates predicted tertiary '
                                      'structures, otherwise they are loaded from pdb_path')
        self.parser.add_argument('--tertiary_structure_method', type=str, default=None,
                                 choices=['esmfold'],
                                 help='3D structure prediction method. None indicates to load existing tertiary '
                                      'structures from PDB files, otherwise, sequences in input CSV file are '
                                      'predicted using the specified method')
        self.parser.add_argument('--pdb_path', type=Path, required=False,
                                 help='Path to load tertiary structures')
        self.parser.add_argument('--amino_acid_representation', type=str, default='CA',
                                 choices=['CA'],
                                 help='Amino acid representations')
        self.parser.add_argument('--minimum_sequence_length', type=int, default=10,
                                 help='Minimum sequence length')
        self.parser.add_argument('--maximum_sequence_length', type=int, default=100,
                                 help='Maximum sequence length')
        self.parser.add_argument('--batch_size', type=int, default=512,
                                 help='Batch size')
        self.parser.add_argument('--distance_intervals_json_path', type=Path, required=False,
                                 help='Path to json file with distance intervals')
        self.parser.add_argument('--output_path', type=Path, required=False,
                                 help=' The path to save the outputs')

    def get_graph_analyzer_arguments(self) -> Dict:
        self._add_common_arguments()
        args = self.parser.parse_args()
        return vars(args)

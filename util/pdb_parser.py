import warnings
from pathlib import Path

from Bio.PDB import PDBParser
from Bio.PDB.PDBExceptions import PDBConstructionWarning
warnings.simplefilter('ignore', PDBConstructionWarning)
import io
import numpy as np


def save_pdb(pdb_str, pdb_name, path: Path):
    with open(path.joinpath(pdb_name + ".pdb"), "w") as f:
        f.write(pdb_str)


def open_pdb(pdb_file):
    with open(pdb_file, "r") as f:
        pdb_str = f.read()
        return pdb_str


def get_atom_coordinates_from_pdb(pdb_str, atom_type='CA'):
    try:
        pdb_filehandle = io.StringIO(pdb_str)
        parser = PDBParser(QUIET=True)
        structure = parser.get_structure("pdb", pdb_filehandle)

        atom_coordinates = []
        for model in structure:
            for chain in model:
                for residue in chain:
                    if residue.has_id(atom_type):
                        atom = residue[atom_type]
                        atom_coordinates.append(np.float64(atom.coord))

        pdb_filehandle.close()
        return atom_coordinates

    except Exception as e:
        raise ValueError(f"Error parsing the PDB structure: {e}")

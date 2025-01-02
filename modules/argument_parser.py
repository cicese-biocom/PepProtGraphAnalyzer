from datetime import datetime
from enum import Enum, auto
from pathlib import Path
from pydantic_computed import computed, Computed
from pydantic.v1 import BaseModel, Field, root_validator, FilePath, DirectoryPath
import pydantic_argparse
from typing import Optional, Dict, Literal
from utils import json_parser


class TertiaryStructurePredictionMethod(Enum):
    esmfold = auto()
    alphafold = auto()


PREDICTION_METHODS = {TertiaryStructurePredictionMethod.esmfold}
LOAD_METHODS = {TertiaryStructurePredictionMethod.esmfold, TertiaryStructurePredictionMethod.alphafold}


class CommonArguments(BaseModel):
    dataset: FilePath = Field(
        description="Path to the input dataset in csv format."
    )

    predict_tertiary_structure: Optional[bool] = Field(
        default=False,
        description="True if specified, otherwise, False. True indicates predicted tertiary structures, "
                    "otherwise they are loaded from pdb_path."
    )

    tertiary_structure_method: TertiaryStructurePredictionMethod = Field(
        description=""
    )

    pdb_path: DirectoryPath = Field(
        description="Path where tertiary structures are saved in or loaded from PDB files."
    )

    minimum_sequence_length: Optional[int] = Field(
        default=None,
        description="Minimum sequence length."
    )

    maximum_sequence_length: Optional[int] = Field(
        default=None,
        description="Maximum sequence length."
    )

    batch_size: Optional[int] = Field(
        default=512,
        description="Batch size"
    )

    output_path: DirectoryPath = Field(
        description="The path to save the outputs"
    )

    amino_acid_representation: Optional[Literal['CA']] = Field(
        default='CA',
        description="Amino acid representations"
    )

    @root_validator
    def validator(cls, values):
        predict_tertiary_structure = values.get("predict_tertiary_structure")
        tertiary_structure_method = values.get("tertiary_structure_method")

        if predict_tertiary_structure:
            if tertiary_structure_method not in PREDICTION_METHODS:
                raise ValueError(
                    f"The method '{tertiary_structure_method}' is not valid for predicting tertiary structures. "
                    f"Valid methods are: {', '.join(m.name for m in PREDICTION_METHODS)}."
                )
        else:
            if tertiary_structure_method not in LOAD_METHODS:
                raise ValueError(
                    f"The method '{tertiary_structure_method}' is not valid for loading tertiary structures. "
                    f"Valid methods are: {', '.join(m.name for m in LOAD_METHODS)}."
                )

        # output paths
        values['output_paths'] = cls.output_paths(**values)

        # distance function
        values['distance_functions'] = ['euclidean', 'canberra', 'lance_williams', 'clark', 'soergel', 'bhattacharyya',
                                        'angular_separation']

        return values

    def output_paths(**kwargs):
        output_path = kwargs.get('output_path')
        mode = kwargs.get('mode')
        mode_path_name = kwargs.get('mode_path_name')

        # create output path
        current_time = datetime.now().replace(microsecond=0).isoformat().replace(':', '.')
        output_path = output_path.joinpath(f"{current_time}-{mode_path_name}")
        output_path.mkdir(parents=True)

        # load output path settings
        settings_file = Path('settings/output_settings.json').resolve()
        data = json_parser.load_json(settings_file)

        # create output file paths
        paths = {}
        for setting in data["output_settings"]:
            if mode in setting["modes"]:
                paths[setting["key"]] = output_path.joinpath(setting["name"])
                paths[setting["key"]].mkdir(parents=True, exist_ok=True)

                for file in setting.get("files", []):
                    paths[file["key"]] = paths[setting["key"]].joinpath(file["name"])
        return paths


class DataIngestion(CommonArguments):
    mode: str = Field("data_ingestion", const=True)
    mode_path_name: str = Field("Data_Ingestion", const=True)


class GraphAnalyzerArguments(CommonArguments):
    mode: str = Field("graph_analyzer", const=True)
    mode_path_name: str = Field("Graph_Analyzer", const=True)

    distance_intervals_json_path: Optional[DirectoryPath] = Field(
        description="Path to json file with distance intervals"
    )


def argument_parser(mode: str):
    model = {
        'data_ingestion': DataIngestion,
        'graph_analyzer': GraphAnalyzerArguments
    }

    parser = pydantic_argparse.ArgumentParser(model=model[mode], exit_on_error=False)
    arguments = parser.parse_typed_args()
    return arguments

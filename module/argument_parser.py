from enum import Enum, auto

from dotenv import load_dotenv
from pydantic import PositiveInt, PositiveFloat
from pydantic.v1 import BaseModel, Field, root_validator, FilePath, DirectoryPath
import pydantic_argparse
from typing import Optional, Literal, List, Annotated
from module.distance import EuclideanDistance, CanberraDistance, LanceWilliamsDistance, ClarkDistance, SoergelDistance, \
    BhattacharyyaDistance, AngularSeparationDistance
from util.json_parser import get_distance_intervals, output_config


class TertiaryStructurePredictionMethod(Enum):
    esmfold = auto()
    alphafold = auto()


distance_function_map = {
    'euclidean': EuclideanDistance(),
    'canberra': CanberraDistance(),
    'lance_williams': LanceWilliamsDistance(),
    'clark': ClarkDistance(),
    'soergel': SoergelDistance(),
    'bhattacharyya': BhattacharyyaDistance(),
    'angular_separation': AngularSeparationDistance()
}
DISTANCE_FUNCTIONS = list(distance_function_map.keys())
DISTANCE_STRATEGIES = list(distance_function_map.values())

PREDICTION_METHODS = {TertiaryStructurePredictionMethod.esmfold}
LOAD_METHODS = {TertiaryStructurePredictionMethod.esmfold, TertiaryStructurePredictionMethod.alphafold}


class CommonArguments(BaseModel):
    dataset: FilePath = Field(
        description="Path to the input dataset in csv format."
    )

    output_path: DirectoryPath = Field(
        description="The path to save the outputs"
    )

    @root_validator
    def validator(cls, values):
        # distance functions
        values['distance_functions'] = DISTANCE_FUNCTIONS

        # output paths
        values['output_paths'] = output_config(**values)

        return values


class DataIngestionArguments(CommonArguments):
    mode: str = Field("data_ingestion", const=True)
    mode_path_name: str = Field("Data_Ingestion", const=True)

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

    amino_acid_representation: Optional[Literal['CA']] = Field(
        default='CA',
        description="Amino acid representations"
    )

    batch_size: Optional[int] = Field(
        default=512,
        description="Batch size"
    )

    @root_validator
    def validator(cls, values):
        super(DataIngestionArguments, cls).validator(values)
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

        # distance strategy
        values['distance_strategies'] = DISTANCE_STRATEGIES

        return values


class GraphAnalyzerArguments(CommonArguments):
    mode: str = Field("graph_analyzer", const=True)
    mode_path_name: str = Field("Graph_Analyzer", const=True)

    distance_intervals_json: FilePath = Field(
        description="Path to json file with distance intervals"
    )

    batch_size: Annotated[Optional[PositiveInt], Field(description='Batch size')] = 1000

    graph_similarity_functions: List[Literal['cosine_similarity', 'graph_edit_distance', 'optimize_graph_edit_distance']] = Field(description='Functions to calculate similarities')

    ged_timeout: Annotated[Optional[PositiveFloat],
                           Field(description="Maximum number of seconds to execute. After timeout is met, the current best GED is returned.")]

    batch_size: Optional[int] = Field(
        default=512,
        description="Batch size"
    )

    @root_validator
    def validator(cls, values):
        super(GraphAnalyzerArguments, cls).validator(values)

        # graph similarity functions
        if 'graph_edit_distance' in values['graph_similarity_functions'] and 'optimize_graph_edit_distance' in values['graph_similarity_functions']:
            raise ValueError(
                "Only one of 'graph_edit_distance' or 'optimize_graph_edit_distance' can be used at the same time.")

        # ged_timeout parameter
        if 'graph_edit_distance' not in values['graph_similarity_functions'] and values['ged_timeout']:
            raise ValueError(
                f"The graph similarity functions '{','.join(values['graph_similarity_functions'])}' "
                f"do not require the parameter 'ged_timeout'."
            )

        # distance intervals json
        values['distance_intervals'] = get_distance_intervals(values['distance_intervals_json'])
        del values['distance_intervals_json']

        values['random_graph_sim_funcs'] = ['cosine_similarity']

        return values


class SequenceAnalyzerArguments(CommonArguments):
    mode: str = Field("sequence_analyzer", const=True)
    mode_path_name: str = Field("Sequence_Analyzer", const=True)

    batch_size: Optional[int] = Field(
        default=512,
        description="Batch size"
    )

    @root_validator
    def validator(cls, values):
        super(SequenceAnalyzerArguments, cls).validator(values)
        return values


def argument_parser(mode: str):
    model = {
        'data_ingestion': DataIngestionArguments,
        'sequence_analyzer': SequenceAnalyzerArguments,
        'graph_analyzer': GraphAnalyzerArguments
    }

    load_dotenv(dotenv_path='.env')
    parser = pydantic_argparse.ArgumentParser(model=model[mode], exit_on_error=False)
    arguments = parser.parse_typed_args()
    return arguments

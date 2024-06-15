from pathlib import Path

import pandas as pd
import numpy as np
import math
from plotnine import (
    ggplot, aes, geom_histogram, theme_minimal,
    scale_x_continuous, scale_y_continuous, theme,
    element_text, labs, scale_y_log10, after_stat,
    guide_colorbar, geom_tile, scale_fill_gradient2
)
from plotnine.exceptions import PlotnineWarning
import warnings

warnings.filterwarnings("ignore", category=PlotnineWarning)


def plot_inter_amino_acid_distances(distance_filepath, distance_function, x_axis_step, binwidth, output_filepath):
    inter_amino_acid_distances = pd.read_csv(distance_filepath, header=None, names=['inter_amino_acid_distances'])

    start = 0
    stop = math.ceil(inter_amino_acid_distances['inter_amino_acid_distances'].max())
    xticks = np.arange(start, stop + x_axis_step, x_axis_step)

    max_number_of_sequences = len(inter_amino_acid_distances)

    plot = (
            ggplot(inter_amino_acid_distances, aes(x="inter_amino_acid_distances", y=after_stat("count")))
            + geom_histogram(fill="#a9ceea", color="#1b4f72", binwidth=binwidth)
            + scale_x_continuous(breaks=xticks)
            + scale_y_continuous(
                labels=lambda y: _format_labels(y, max_number_of_sequences),
                sec_trans=lambda y: _transform_data(y, max_number_of_sequences)
            )
            + labs(
                title="",
                x=f'{process_distance_name(distance_function)} distance-based Threshold',
                y="Frequency"
              )
            + theme_minimal()
    )

    create_path(output_filepath)
    plot.save(output_filepath, dpi=300)
    return plot


def create_merge_similarity_matrix(graph_similarity_1, graph_similarity_2, intervals, matrix_output_path):
    graph_similarity = merge_graph_similarity_data(graph_similarity_1, graph_similarity_2)
    
    filtered_graph_similarity = graph_similarity[
        (graph_similarity['distance_interval_1'].isin(intervals)) &
        (graph_similarity['distance_interval_2'].isin(intervals))
        ].reset_index(drop=True)

    similarity_matrix = pd.DataFrame(0.0, index=intervals, columns=intervals)
    similarity_matrix_1 = pd.DataFrame(0.0, index=intervals, columns=intervals)
    similarity_matrix_2 = pd.DataFrame(0.0, index=intervals, columns=intervals)

    for _, row in filtered_graph_similarity.iterrows():
        interval1 = row['distance_interval_1']
        interval2 = row['distance_interval_2']
        average_similarity_1 = row['average_similarity_1']
        average_similarity_2 = row['average_similarity_2']

        similarity_matrix.loc[interval1, interval2] = average_similarity_2
        similarity_matrix.loc[interval2, interval1] = average_similarity_1

        similarity_matrix_1.loc[interval1, interval2] = average_similarity_1
        similarity_matrix_1.loc[interval2, interval1] = average_similarity_1

        similarity_matrix_2.loc[interval1, interval2] = average_similarity_2
        similarity_matrix_2.loc[interval2, interval1] = average_similarity_2

    create_path(matrix_output_path)

    similarity_matrix.to_csv(f'{matrix_output_path}Similarity Matrix-merged.csv', index=True, header=True)
    similarity_matrix_1.to_csv(f'{matrix_output_path}Similarity Matrix-1.csv', index=True, header=True)
    similarity_matrix_2.to_csv(f'{matrix_output_path}Similarity Matrix-2.csv', index=True, header=True)
    
    return similarity_matrix


def plot_merge_similarity_matrix(similarity_matrix, x_axis_label, y_axis_label, output_filepath):
    similarity_matrix_reset = similarity_matrix.reset_index().melt(id_vars='index')
    similarity_matrix_reset.columns = ['distance_interval_1', 'distance_interval_2', 'average_similarity']

    plot = (
            ggplot(similarity_matrix_reset,
                   aes(x='distance_interval_1', y='distance_interval_2', fill='average_similarity'))
            + geom_tile()
            + scale_fill_gradient2(
                low="#cf885f",
                mid="#9ac7e1",
                high="#3481ad",
                midpoint=0,
                aesthetics="fill",
                na_value="#08bed3",
                limits=(-1.000001, 1.00001),
                breaks=np.arange(-1, 1.25, 0.25),
                guide=guide_colorbar(title="Cosine Similarity"),
                expand=(0, 0, 0, 1)
            )
            + labs(
                x=f'{x_axis_label}',
                y=f'{y_axis_label}'
            )
            + theme_minimal()
            + theme(axis_text_x=element_text(angle=45, hjust=1))
    )

    create_path(output_filepath)
    plot.save(f'{output_filepath}Similarity Cosine.png', dpi=300)
    return plot


def _format_labels(x, max_number_of_sequences):
    return [f"{int(xi / 1000)}k" for xi in x]


def _transform_data(y, max_number_of_sequences):
    return y * max_number_of_sequences / 1000


def process_distance_name(distance_name):
    words = distance_name.split('_')
    capitalized_words = [word.capitalize() for word in words]
    result = ' '.join(capitalized_words)
    return result
    

def merge_graph_similarity_data(graph_similarity_1, graph_similarity_2):    
    graph_similarity_1 = graph_similarity_1.rename(columns={'average_similarity': 'average_similarity_1'})    
    graph_similarity_2 = graph_similarity_2.rename(columns={'average_similarity': 'average_similarity_2'})
    return pd.merge(graph_similarity_1, graph_similarity_2, on=['distance_interval_1', 'distance_interval_2'])


def create_path(output_filepath):
    output_filepath = Path(output_filepath)

    if output_filepath.suffix:
        output_filepath.parent.mkdir(parents=True, exist_ok=True)
    else:
        output_filepath.mkdir(parents=True, exist_ok=True)
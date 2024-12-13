from pathlib import Path
from tqdm import tqdm
import pandas as pd
import numpy as np
import math
from plotnine import (
    ggplot, aes, geom_histogram, theme_minimal,
    scale_x_continuous, scale_y_continuous, theme,
    element_text, labs, scale_y_log10, after_stat,
    guide_colorbar, geom_tile, scale_fill_gradient2,
    geom_boxplot, scale_fill_manual, scale_color_manual, 
    geom_line, aes, geom_segment, labs, scale_x_discrete,
    element_rect, element_blank, element_line
)

from plotnine import (
    ggplot, geom_boxplot, 
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
            + geom_histogram(fill="white", color="blue", binwidth=binwidth, boundary=0)
            + scale_x_continuous(breaks=xticks, expand=(0.002, 0.002))
            + scale_y_continuous(
                labels=lambda y: _format_labels(y, max_number_of_sequences),
                sec_trans=lambda y: _transform_data(y, max_number_of_sequences),
                expand=(0.005, 0.005) 
            )
            + labs(
                title="",
                #x=f'{process_distance_name(distance_function)} distance-based Threshold',
                x=f'{process_distance_name(distance_function)} distance-based intervals',
                #y="Frequency"
                y="Number of Inter-Amino Acid Relationships"
              )
            + theme(
                figure_size=(10, 6),
                panel_background=element_rect(fill='white'),  # Fondo del gráfico blanco
                panel_grid_major=element_blank(),  # Eliminar la cuadrícula mayor
                panel_grid_minor=element_blank(),  # Eliminar la cuadrícula menor
                axis_text_x=element_text(size = 14, color='black'),
                axis_text_y=element_text(size = 14, color='black'),
                axis_title_x=element_text( size = 14, color='black'),
                axis_title_y=element_text(size = 14, color='black'),
                legend_position='none',  # Eliminar la leyenda
                plot_background=element_rect(fill=None, size=1),  # Borde alrededor del gráfico
                panel_border=element_rect(fill=None, size=0.5),  # Borde alrededor del panel de gráficos
                axis_line=element_line( size=0.5)  # Borde interno de los ejes
            )
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
                low="#faab00",
                mid="#e7ecef",
                high="#0a2130",
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


def plot_density(input_filepath, output_filepath):
    # Load the data
    graph_info = pd.read_csv(input_filepath)
    
    # Get unique max_intervals for each distance_function
    intervals = graph_info.groupby('distance_function')['max_interval'].unique()
    
    # Create a dictionary to map max_interval values to I1, I2, I3
    interval_map = {}
    for distance_function, unique_intervals in intervals.items():
        # Sort intervals to ensure correct mapping
        sorted_intervals = sorted(unique_intervals)
        interval_map.update({(distance_function, sorted_intervals[0]): 'I1'})
        interval_map.update({(distance_function, sorted_intervals[1]): 'I2'})
        interval_map.update({(distance_function, sorted_intervals[2]): 'I3'})
    
    # Add the new 'interval' column based on the mapping
    graph_info['interval'] = graph_info.apply(
        lambda row: interval_map[(row['distance_function'], row['max_interval'])], axis=1)

    distance_order = ['euclidean', 'angular_separation', 'bhattacharyya', 'canberra', 'clark', 'lance_williams', 'soergel']
    graph_info['distance_function'] = pd.Categorical(graph_info['distance_function'], categories=distance_order, ordered=True)
    
    colors = ["#1f77b4", "#ff7f0e", "#2ca02c"]

    # boxplot
    plot = (
            ggplot(graph_info, aes(x='distance_function', y='density', fill='factor(interval)')) 
            + geom_boxplot()
            + scale_fill_manual(values=colors)
            + labs(
                  title="",
                  x=f'Función de distancia',
                  y=f'Densidad',
                  fill='Interval')  
            + theme_minimal()
            # + theme(axis_text_x=element_text(angle=45, hjust=1)))
            + theme(
                figure_size=(10, 6),
                panel_background=element_rect(fill='white'),  # Fondo del gráfico blanco
                panel_grid_major=element_blank(),  # Eliminar la cuadrícula mayor
                panel_grid_minor=element_blank(),  # Eliminar la cuadrícula menor
                axis_text_x=element_text(family = "Times New Roman", size = 18, color='black'),
                axis_text_y=element_text(family = "Times New Roman", size = 18, color='black'),
                axis_title_x=element_text(family = "Times New Roman", size = 18, color='black'),
                axis_title_y=element_text(family = "Times New Roman", size = 18, color='black'),
                legend_position='none',  # Eliminar la leyenda
                plot_background=element_rect(fill=None, size=1),  # Borde alrededor del gráfico
                panel_border=element_rect(fill=None, size=0.5),  # Borde alrededor del panel de gráficos
                axis_line=element_line( size=0.5)  # Borde interno de los ejes
            ))
    
    create_path(output_filepath)
    plot.save(output_filepath, dpi=300)
    return plot, graph_info


def plot_edges(input_filepath, output_filepath):
    # Load the data
    graph_info = pd.read_csv(input_filepath)
    
    # Get unique max_intervals for each distance_function
    intervals = graph_info.groupby('distance_function')['max_interval'].unique()
    
    # Create a dictionary to map max_interval values to I1, I2, I3
    interval_map = {}
    for distance_function, unique_intervals in intervals.items():
        # Sort intervals to ensure correct mapping
        sorted_intervals = sorted(unique_intervals)
        interval_map.update({(distance_function, sorted_intervals[0]): 'I1'})
        interval_map.update({(distance_function, sorted_intervals[1]): 'I2'})
        interval_map.update({(distance_function, sorted_intervals[2]): 'I3'})
    
    # Add the new 'interval' column based on the mapping
    graph_info['interval'] = graph_info.apply(
        lambda row: interval_map[(row['distance_function'], row['max_interval'])], axis=1)
    
    colors = ["#1f77b4", "#ff7f0e", "#2ca02c"]
    
    plot = (
            ggplot(graph_info, aes(x='distance_function', y='number_of_edges', fill='factor(interval)')) 
            + geom_boxplot()
            + scale_fill_manual(values=colors)
            + labs(
                  title="",
                  x=f'Función de distancia',
                  y=f'Densidad',
                  fill='Interval')  
            + theme_minimal()
            + theme(axis_text_x=element_text(angle=45, hjust=1)))
    
    create_path(output_filepath)
    plot.save(output_filepath, dpi=300)
    return plot, graph_info


def plot_density_vs_number_of_nodes_per_distance_function(graph_info, output_filepath, distance_function):
    filtered_data = graph_info[graph_info['distance_function'] == distance_function]    
    
    colors = ["#1f77b4", "#ff7f0e", "#2ca02c"]
    
    plot = (
        ggplot(filtered_data, aes(x='number_of_nodes', y='density', color='interval', group='interval'))
        + geom_line()
        + scale_color_manual(values=colors)
        + labs(
            x='Sequence Length',
            y='Density',
            color='Interval'
        )
        + theme_minimal()
        + theme(
            axis_text_x=element_text(angle=45, hjust=1)
        )
    )
    
    create_path(output_filepath)
    plot.save(output_filepath, dpi=300)
    return plot


def plot_desity_vs_number_of_nodes_per_distance_function(graph_info, output_filepath, distance_function):
    filtered_data = graph_info[graph_info['distance_function'] == distance_function]    
    
    colors = ["#1f77b4", "#ff7f0e", "#2ca02c"]
    
    plot = (
        ggplot(filtered_data, aes(x='number_of_nodes', y='density', color='interval', group='interval')) 
        + geom_line()
        + scale_color_manual(values=colors)
        + labs(
            x='Sequence Length',
            y='Density',
            color='Interval'
        ) 
        + theme_minimal()
        + theme(
            axis_text_x=element_text(angle=45, hjust=1)
        )
    )
    
    create_path(output_filepath)
    plot.save(output_filepath, dpi=300)
    return plot


def plot_number_of_edges_vs_number_of_nodes_per_distance_function(graph_info, output_filepath, distance_function):
    filtered_data = graph_info[graph_info['distance_function'] == distance_function]    
    
    colors = ["#1f77b4", "#ff7f0e", "#2ca02c"]
    
    plot = (
        ggplot(filtered_data, aes(x='number_of_nodes', y='number_of_edges', color='interval', group='interval')) 
        + geom_line() 
        + scale_color_manual(values=colors) 
        + labs(
            x='Sequence Length',
            y='Number of Edges',
            color='Interval'
        ) 
        + theme(
            axis_text_x=element_text(angle=45, hjust=1)
        )
    )
    
    create_path(output_filepath)
    plot.save(output_filepath, dpi=300)
    return plot


def statistics(base_path, distance_functions, output_filepath, percentiles):
    all_data = []
    for distance_function in tqdm(distance_functions, desc="Processing distance functions"):
        distance_filepath = f'{base_path}Inter_Amino_Acid_Distances-{distance_function}.csv'
        distance_info = pd.read_csv(distance_filepath, header=None, names=['inter_amino_acid_distances'])
    
        distance_info['distance_function'] = distance_function
        all_data.append(distance_info)
    
    all_data = pd.concat(all_data, ignore_index=True)
    stats_by_function = all_data.groupby('distance_function', observed=True)['inter_amino_acid_distances'].describe(percentiles=percentiles)
    
    stats_by_function = stats_by_function.reset_index()
    stats_by_function.to_csv(output_filepath, index=False)
    
    return stats_by_function


from scipy.stats import skew, kurtosis
import pandas as pd
from tqdm import tqdm

def statistics2(base_path, distance_functions, output_filepath, percentiles):
    all_data = []
    
    # Leer y procesar archivos de distancias
    for distance_function in tqdm(distance_functions, desc="Processing distance functions"):
        distance_filepath = f'{base_path}Inter_Amino_Acid_Distances-{distance_function}.csv'
        distance_info = pd.read_csv(distance_filepath, header=None, names=['inter_amino_acid_distances'])
    
        distance_info['distance_function'] = distance_function
        all_data.append(distance_info)
    
    # Concatenar todos los datos
    all_data = pd.concat(all_data, ignore_index=True)
    
    # Calcular estadísticas descriptivas
    stats_by_function = all_data.groupby('distance_function')['inter_amino_acid_distances'].describe(percentiles=percentiles)
    
    # Calcular Skewness y Kurtosis para cada grupo
    skew_kurt_stats = all_data.groupby('distance_function')['inter_amino_acid_distances'].agg(
        skewness=lambda x: skew(x, nan_policy='omit'),
        kurtosis=lambda x: kurtosis(x, nan_policy='omit', fisher=True)
    )
    
    # Combinar estadísticas descriptivas con Skewness y Kurtosis
    stats_by_function = stats_by_function.reset_index().merge(
        skew_kurt_stats.reset_index(),
        on='distance_function',
        how='left'
    )
    
    # Guardar estadísticas en un archivo CSV
    stats_by_function.to_csv(output_filepath, index=False)
    
    return stats_by_function


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
import pandas as pd
import numpy as np
import math
from plotnine.data import mpg
from plotnine import ggplot, aes, geom_histogram, geom_bar, theme_minimal, scale_x_continuous, scale_y_continuous, theme, element_text, labs, scale_y_log10, after_stat
from plotnine.exceptions import PlotnineWarning
import warnings
warnings.filterwarnings("ignore", category=PlotnineWarning)


def plot_inter_amino_acid_distances(distance_filepath, distance_function, x_axis_step, output_filepath):
    inter_amino_acid_distances = pd.read_csv(distance_filepath, header=None, names=['inter_amino_acid_distances'])
    
    start = 0
    stop = math.ceil(inter_amino_acid_distances['inter_amino_acid_distances'].max())
    xticks = np.arange(start, stop + x_axis_step, x_axis_step)
    
    max_number_of_sequences = len(inter_amino_acid_distances)
    
    graphic = (
        ggplot(inter_amino_acid_distances, aes(x="inter_amino_acid_distances", y=after_stat("count"))) 
        + geom_histogram(fill="#a9ceea", color="#1b4f72")
        + scale_x_continuous(breaks=xticks)
        + scale_y_continuous(labels=_format_labels, sec_trans=_transform_data)
        + labs(title = "", x = f'{process_distance_name(distance_function)} distance-based Threshold', y = "Frequency")
        + theme_minimal()
    )
    
    graphic.save(output_filepath, dpi=300)
    return graphic


def _format_labels(x):
    if isinstance(x, list):  # Verifica si x es una lista
        return [f"{int(xi / 1000)}k" for xi in x]  # Formatea cada elemento de la lista
    else:
        if x == 0:
            return "0"
        else:
            return f"{int(x / 1000)}k"

def _transform_data(y):
    return y * max_number_of_sequences / 1000


def process_distance_name(distance_name):
    words = distance_name.split('_')
    capitalized_words = [word.capitalize() for word in words]
    result = ' '.join(capitalized_words)

    return result
    
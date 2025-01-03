import numpy as np
from matplotlib import pyplot as plt
import pandas as pd

# Times New Roman equivalents:  Liberation Serif, Linux Libertine
FONT = 'Liberation Serif'


# histogram
def histogram(data, x_labels, y_label, bin_width=None, x_axis_step=None, x_axis_max=None, output=None, fig_size=(6, 4),
              x_label_fontsize=10, y_label_fontsize=10, x_ticks_fontsize=8, y_ticks_fontsize=8, n_rows=None, n_cols=None, titles=None):
    plt.rcParams['font.family'] = FONT

    if isinstance(data, pd.Series):
        data = data.to_frame()

    column_names = data.columns
    num_subplots = len(column_names)

    n_rows, n_cols = _calculate_layout(num_subplots, n_rows, n_cols)

    fig, axs = plt.subplots(n_rows, n_cols, figsize=(n_cols * fig_size[0], n_rows * fig_size[1]), constrained_layout=True)

    axs = np.array(axs).reshape(-1)

    if not isinstance(x_labels, list):
        x_labels = [x_labels] * num_subplots
    if not isinstance(bin_width, list):
        bin_width = [bin_width] * num_subplots
    if not isinstance(x_axis_step, list):
        x_axis_step = [x_axis_step] * num_subplots

    for i, column in enumerate(column_names):
        data_column = data[column]

        bins = None
        if bin_width[i] is not None:
            bins = np.arange(data_column.min(), data_column.max() + bin_width[i], bin_width[i])

        axs[i].hist(
            data_column,
            color='white',
            edgecolor='blue',
            alpha=0.7,
            bins=bins,
        )

        axs[i].set_xlabel(x_labels[i], fontsize=x_label_fontsize, labelpad=15)
        axs[i].tick_params(axis='x', labelsize=x_ticks_fontsize)
        axs[i].tick_params(axis='y', labelsize=y_ticks_fontsize)
        axs[i].set_xlim(left=0.01)

        x_max = x_axis_max if x_axis_max is not None else data_column.max()
        if x_axis_step[i] is not None:
            axs[i].xaxis.set_ticks(np.arange(0, x_max + 0.01, x_axis_step[i]))

        axs[i].grid(False)
        axs[i].spines['top'].set_visible(False)
        axs[i].spines['right'].set_visible(False)
        axs[i].spines['left'].set_linewidth(0.5)
        axs[i].spines['bottom'].set_linewidth(0.5)

        # Add title to the right if provided
        if titles is not None and len(titles) == num_subplots:
            axs[i].set_title(titles[i], loc='right', fontsize=x_label_fontsize)

    axs[0].set_ylabel(y_label, fontsize=y_label_fontsize, labelpad=15)

    for j in range(num_subplots, len(axs)):
        axs[j].axis('off')

    if output:
        plt.savefig(f'{output}.png', dpi=300, bbox_inches='tight')

    plt.show()

    return plt


# boxplot
def boxplot(data, x_axis, y_axis, x_label, y_label, x_ticks=None, y_lim=None, categories=None,
            output=None, fig_size=(6, 4), x_label_fontsize=10, y_label_fontsize=10, x_ticks_fontsize=8, y_ticks_fontsize=8):
    plt.rcParams['font.family'] = FONT

    # Convert x_axis to string type
    data[x_axis] = data[x_axis].astype(str)

    # Convert to categorical type with or without a specified label_order_x
    if categories:
        data[x_axis] = pd.Categorical(data[x_axis], categories=categories, ordered=True)
    else:
        data[x_axis] = pd.Categorical(data[x_axis])

    # Create the box plot
    plt.figure(figsize=fig_size)

    box = plt.boxplot(
        [data[data[x_axis] == cat][y_axis] for cat in data[x_axis].cat.categories],
        patch_artist=True,  # Fill the boxes with color
        # showmeans=True,  # Do not show the mean
        widths=0.43  # Control the width of the boxes
    )

    for patch in box['boxes']:
        patch.set(facecolor='white', edgecolor='blue', linewidth=0.8)

    for whisker in box['whiskers']:
        whisker.set(color='black', linewidth=0.6, linestyle="--")

    for cap in box['caps']:
        cap.set(color='black', linewidth=0.6)

    for median in box['medians']:
        median.set(color='red', linewidth=0.8)

    for flier in box['fliers']:
        flier.set(marker='+', color='#ff0000', markersize=5, alpha=1)

    # Customize x-tick labels
    if x_ticks is None:
        x_ticks = data[x_axis].cat.categories

    plt.xticks(
        ticks=range(1, len(data[x_axis].cat.categories) + 1),
        labels=x_ticks,
        fontsize=x_ticks_fontsize
    )

    plt.yticks(
        fontsize=y_ticks_fontsize
    )

    # Customize labels
    plt.xlabel(
        x_label,
        fontsize=x_label_fontsize,
        labelpad=15
    )

    plt.ylabel(
        y_label,
        fontsize=y_label_fontsize,
        labelpad=15
    )

    if y_lim is not None:
        ylim_min, ylim_max = y_lim

        if ylim_min is not None and ylim_max is not None and ylim_min < ylim_max:
            plt.ylim(ylim_min, ylim_max)

    # Remove the grid
    plt.grid(False)

    # Add a border around the plot
    plt.gca().spines['top'].set_visible(0.5)
    plt.gca().spines['right'].set_visible(0.5)
    plt.gca().spines['left'].set_linewidth(0.5)
    plt.gca().spines['bottom'].set_linewidth(0.5)

    # Save the plot
    if output:
        plt.savefig(f'{output}.png', dpi=300, bbox_inches='tight')

    # Show the plot
    return plt


# bar_chart
def bar_chart(data, x_axis, y_axis, x_label, y_label, output=None, fig_size=(6, 4), x_label_fontsize=10, y_label_fontsize=10,
              x_ticks_fontsize=8, y_ticks_fontsize=8, x_ticks_rotation=None):
    plt.rcParams['font.family'] = FONT

    plt.figure(figsize=fig_size)

    x = data[x_axis]
    y = data[y_axis]

    plt.bar(x, y, color='white', alpha=0.7, edgecolor='blue')

    plt.xlabel(x_label, fontsize=x_label_fontsize, labelpad=15)
    plt.ylabel(y_label, fontsize=y_label_fontsize, labelpad=15)

    plt.xticks(rotation=x_ticks_rotation, fontsize=x_ticks_fontsize)
    plt.yticks(fontsize=y_ticks_fontsize)

    plt.grid(False)

    # Add a border around the plot
    plt.gca().spines['top'].set_visible(0.5)
    plt.gca().spines['right'].set_visible(0.5)
    plt.gca().spines['left'].set_linewidth(0.5)
    plt.gca().spines['bottom'].set_linewidth(0.5)

    plt.tight_layout()

    if output:
        plt.savefig(f'{output}.png', dpi=300, bbox_inches='tight')

    return plt


def _calculate_layout(num_subplots, n_rows=None, n_cols=None):
    if n_rows is None and n_cols is None:
        n_rows = 1
        n_cols = num_subplots

    if n_rows is not None:
        # Calculate the number of columns
        n_rows = min(n_rows, num_subplots)
        n_cols = -(-num_subplots // n_rows)  # Ceiling division
    elif n_cols is not None:
        # Calculate the number of rows
        n_cols = min(n_cols, num_subplots)
        n_rows = -(-num_subplots // n_cols)  # Ceiling division

    if n_rows * n_cols < num_subplots:
        raise ValueError(f"The layout with {n_rows} rows and {n_cols} columns cannot fit {num_subplots} subplots.")

    return n_rows, n_cols




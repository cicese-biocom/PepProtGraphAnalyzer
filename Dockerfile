FROM jupyter/minimal-notebook

# Conda environment
COPY ./environment.yml /home/jovyan/environment.yml
RUN conda env update --file environment.yml --name base && \
    conda init bash

RUN conda install -c conda-forge jupyterlab=3 "ipykernel>=6" xeus-python

WORKDIR /home/jovyan/work
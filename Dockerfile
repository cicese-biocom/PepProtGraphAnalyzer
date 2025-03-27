FROM nvidia/cuda:11.3.1-cudnn8-devel-ubuntu20.04

# Set non-interactive mode for apt
ENV DEBIAN_FRONTEND=noninteractive

# Update package list and install prerequisites
RUN apt-get update && apt-get install -y \
    software-properties-common \
    wget

# Add deadsnakes PPA for Python 3.10
RUN add-apt-repository ppa:deadsnakes/ppa -y

# Install Python 3.10
RUN apt-get update && apt-get install -y \
    python3.9 \
    python3.9-distutils \
    python3.9-venv \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*
ENV PYTHON_HOME /usr/bin/python3.9
ENV PATH $PYTHON_HOME/bin:$PATH

# Additional tools and packages
RUN apt-get update \
    && apt-get install -y  \
    build-essential \
    wget \
    libopenblas-dev \
    git \
    python3-pip \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install Miniconda
RUN wget -P /tmp \
    "https://repo.anaconda.com/miniconda/Miniconda3-py39_23.9.0-0-Linux-x86_64.sh" \
    && bash /tmp/Miniconda3-py39_23.9.0-0-Linux-x86_64.sh -b -p /opt/conda \
    && rm /tmp/Miniconda3-py39_23.9.0-0-Linux-x86_64.sh
ENV PATH /opt/conda/bin:$PATH

COPY environment.yml .
RUN conda env update --file environment.yml --name base && \
    conda clean -afy && \
    conda init bash

# Set up the working directory
WORKDIR /opt/project

# Command
CMD ["/bin/bash"]
[![Static Badge](https://img.shields.io/badge/Jupyter%20Lab-=3.6.7-orange?style=flat&logo=Jupyter&logoColor=white&labelColor=gray)](https://jupyterlab.readthedocs.io/en/3.6.x/index.html)
[![Docker](https://badgen.net/badge/icon/docker?icon=docker&label)](https://www.docker.com/)
[![Made with Python](https://img.shields.io/badge/Python-=3.11.6-blue?logo=python&logoColor=white)](https://www.python.org/downloads/release/python-3116/)
[![Conda](https://img.shields.io/badge/-conda-44A833?logo=anaconda&logoColor=FFFFFF&color=44A833&labelColor=gray)](https://docs.conda.io/en/latest/)

# Algorithms for Peptide and Protein Graphs

![Image](https://github.com/user-attachments/assets/42c346b6-035b-4236-91f1-0ca30ec83b63)

## **Installation**
Clone the repository using Git:
```
git clone https://github.com/cicese-biocom/algorithms4PepProtGraphs.git
```
The directory structure of the project is as follows:
```
algorithms4PepProtGraphs
├── environment.yml                     <- Python libraries requiered by the notebooks.
├── Dockerfile                          <- Docker image with all the dependencies requiered by the notebooks. 
├── docker-compose.yml                  <- Configuration of the Docker container requiered by the notebooks. 
├── README.md                           <- README to use the notebooks. 
```

### **Dependencies**
The major dependencies used in the notebooks are as follows:

> [Python 3.11.6](https://www.python.org/downloads/release/python-3116/)

The Python libraries used in the notebooks are specified in `environment.yml`.

#### **Python environment configuration via conda**
We provide the steps to create a Python environment from an `environment.yml` file using conda:
```
1. conda env create -f environment.yml
2. conda activate notebooks-env
3. conda env list
```

### **Managing notebooks using Docker container**
We provide the `Dockerfile` and `docker-compose.yml` files with all the dependencies and configurations required by 
the notebooks.
#### Prerequisites:
1. Install Docker following the [Installation Guide](https://docs.docker.com/engine/installation/) for your platform.

#### Build the Docker image locally from the next command line:
```
docker-compose build
```
#### Run the container:
```
docker-compose up
```
#### Once the container is running, you will see the output from the Jupyter server, including a URL to access the notebook. The URL will look like this:
```
http://127.0.0.1:8888/Algorithms4PepProtGraphs/lab
```
#### Copy and paste the URL into your web browser to access the notebooks.
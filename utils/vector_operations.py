import numpy as np


# calculate the vector direction
def calculate_direction(vector):
    magnitude = np.linalg.norm(vector)
    return [component / magnitude for component in vector]


# scalar a vector
def scale_vector(vector, scalar):
    return [component * scalar for component in vector]

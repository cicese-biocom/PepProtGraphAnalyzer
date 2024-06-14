import numpy as np
import itertools


def cosine_similarity(vectors_1, vectors_2):
    similarities = []
    try:
        for vector_a, vector_b in zip(vectors_1, vectors_2):
            similarity = _cosine_similarity(vector_a, vector_b)
            similarities.append(similarity)

        avg_similarity = np.mean(similarities)
        min_similarity = np.min(similarities)
        max_similarity = np.max(similarities)

        return avg_similarity, min_similarity, max_similarity

    except Exception as e:
        raise ValueError(str(e))


def _cosine_similarity(vector_a, vector_b):
    try:
        if len(vector_a) != len(vector_b):
            raise ValueError("The points do not have the same number of coordinates")

        if is_zero_vector(vector_a) or is_zero_vector(vector_b):
            return np.nan

        return np.divide(np.sum(np.multiply(vector_a, vector_b)),
                         np.sqrt(np.dot(np.sum(np.power(vector_a, 2)), np.sum(np.power(vector_b, 2)))))



    except Exception as e:
        raise ValueError(str(e))


def _eigenvalues_non_square_matrices(matrix):
    _, s, _ = np.linalg.svd(matrix)
    eigenvalues = s ** 2
    return eigenvalues


def _eigenvalues_square_matrices(matrix):
    eigenvalues = np.linalg.eigvals(matrix)

    is_symmetric(matrix)

    real_part = np.real(eigenvalues)
    imag_part = np.imag(eigenvalues)

    for i in range(len(eigenvalues)):
        if imag_part[i] > 1e-6:
            raise ValueError(f"Complex eigenvalue found: {eigenvalues[i]}, with imaginary part: {imag_part[i]}")

    return real_part


def eigenvalues(matrix):
    eigen_values = np.linalg.eigvals(matrix)

    real_part = np.real(eigen_values)
    imag_part = np.imag(eigen_values)

    for i in range(len(eigen_values)):
        if imag_part[i] > 1e-6:
            raise ValueError(f"Complex eigenvalue found: {eigen_values[i]}, with imaginary part: {imag_part[i]}")

    return real_part


def calculate_similarity(matrix_a, matrix_b):
    if _is_quare(matrix_a):
        matrix_a_eigenvalues = _eigenvalues_square_matrices(matrix_a)
        matrix_b_eigenvalues = _eigenvalues_square_matrices(matrix_b)
    else:
        matrix_a_eigenvalues = _eigenvalues_non_square_matrices(matrix_a)
        matrix_b_eigenvalues = _eigenvalues_non_square_matrices(matrix_b)

    similarity = _cosine_similarity(matrix_a_eigenvalues, matrix_b_eigenvalues)

    return similarity


def get_similarity(matrices):
    combination_matrices = [(matrix_a, matrix_b) for matrix_a, matrix_b in itertools.combinations(matrices, 2)]
    similarities = [calculate_similarity(matrix_a, matrix_b) for matrix_a, matrix_b in combination_matrices]
    return similarities


def _is_quare(matrix):
    return matrix.shape[0] == matrix.shape[1]


def is_symmetric(matrix):
    if not np.array_equal(matrix, matrix.T):
        raise ValueError("The matrix is not symmetric")
    return True


def is_zero_vector(matrix):
    return np.all(matrix == 0)


def is_zero_matrix(matrix):
    if np.all(matrix == 0):
        print(matrix)


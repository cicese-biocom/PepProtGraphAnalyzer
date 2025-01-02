from itertools import islice


def batch(iterable, batch_size):
    iterator = iter(iterable)
    for first in iterator:
        yield [first] + list(islice(iterator, batch_size - 1))

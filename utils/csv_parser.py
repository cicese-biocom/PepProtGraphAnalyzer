import csv


def add_to_csv(data, filename):
    with open(filename, mode='a', newline='') as file:
        writer = csv.writer(file)
        if all(isinstance(item, (list, tuple)) for item in data):
            writer.writerows(data)
        else:
            writer.writerows([[value] for value in data])




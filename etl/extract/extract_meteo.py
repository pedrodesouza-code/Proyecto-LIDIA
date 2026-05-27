from .base import read_source


def extract(path=None):
    return read_source("METEO", path)

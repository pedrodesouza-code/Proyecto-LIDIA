from .base import read_source


def extract(path=None):
    """Lee detecciones FIRMS previamente obtenidas o exportadas por la fuente."""
    return read_source("FIRMS", path)

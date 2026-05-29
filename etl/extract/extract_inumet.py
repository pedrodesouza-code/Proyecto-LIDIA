from .base import read_source


def extract(path=None):
    """INUMET aplica exclusivamente a estaciones de Uruguay."""
    return read_source("INUMET", path)

"""Vector integration specific exceptions."""


class VectorDatasetException(Exception):
    """Representing an error fetching a dataset for Vector."""


class UnknownCubeException(Exception):
    """Representing an error if the requested cube ID wasn't known."""

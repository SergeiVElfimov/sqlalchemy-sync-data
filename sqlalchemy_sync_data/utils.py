import typing


def batch(objects: list, batch_size: int = 1) -> typing.Generator:
    """Batch list into chunks.

    :param iterable: Iterable object.
    :param batch_size: Max chunk size.
    """
    length = len(objects)
    for ndx in range(0, length, batch_size):
        yield objects[ndx : min(ndx + batch_size, length)]

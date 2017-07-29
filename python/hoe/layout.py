import collections
import json

import numpy as np

_GROUPBY = [
    "address",
    "row",
    "section",
    "slice",
    "strip",
    "stripIndex",
    "topOrBottom",
]


class Layout(object):
    def __init__(self, pixels, rows=216, columns=66, sections=6):
        self.pixels = pixels
        self.n_pixels = len(pixels)
        self.rows = rows
        self.columns = columns
        self.grid = np.zeros((rows, columns), np.int)
        self.sections = 6

        for attr in _GROUPBY:
            setattr(self, attr, collections.defaultdict(list))

        for i, pixel in enumerate(self.pixels):
            self.grid[pixel['row'], pixel['slice']] = i
            for attr in _GROUPBY:
                getattr(self, attr)[pixel[attr]].append(i)

        for attr in _GROUPBY:
            setattr(self, attr, {k: v for k, v in getattr(self, attr).items()})

    def colmod(self, i):
        return divmod(i, self.columns)[1]


# Global Layout for all effects to reference
_layout = None


def init_layout(new_layout):
    global _layout
    if _layout:
        raise RuntimeError("Layout is already initialized")
    _layout = new_layout


def layout():
    return _layout

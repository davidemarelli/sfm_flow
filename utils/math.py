
import logging
from cmath import phase, rect
from math import degrees, radians, sqrt
from typing import List, Union

import numpy as np

from mathutils import Vector

logger = logging.getLogger(__name__)


# ==================================================================================================
def euclidean_distance(p1: Union[Vector, np.array], p2: Union[Vector, np.array]) -> float:
    """Euclidean distance between two 3D points. Support {Vector} and {np.array} as data types.

    Arguments:
        p1 {Union[Vector, np.array]} -- first 3D point
        p2 {Union[Vector, np.array]} -- second 3D point

    Returns:
        float -- euclidean distance
    """
    return sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2 + (p1[2] - p2[2])**2)


# ==================================================================================================
def mean_angle(deg: List[float]) -> float:
    """Compute mean of angles.
    https://rosettacode.org/wiki/Averages/Mean_angle#Python

    Arguments:
        deg {List[float]} -- list of angles in degrees

    Returns:
        float -- mean of angles
    """
    return degrees(phase(sum(rect(1, radians(d)) for d in deg)/len(deg)))

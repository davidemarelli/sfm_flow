
import logging
from cmath import phase, rect
from math import asin, atan2, degrees, pi, radians, sqrt
from typing import List, Tuple, Union

import numpy as np
from mathutils import Matrix, Vector

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


# ==================================================================================================
def matrix_world_to_opk(matrix_world: Matrix) -> Tuple[float, float, float]:
    """Extract Omega, Phi, Kappa angles from a worldspace transformation matrix.

    Omega, Phi, Kappa are CCW rotation along the X, Y, Z axis respectively.
    The order of application is KPO = ZYX (R=Rx*Ry*Rz).

    https://www.geometrictools.com/Documentation/EulerAngles.pdf

    Arguments:
        matrix_world {Matrix} -- worldspace transformation matrix.

    Returns:
        Tuple[float, float, float] -- Omega, Phi, Kappa angles in radians.
    """
    r = matrix_world
    if r[0][2] < 1:
        if r[0][2] > -1:
            thetaY = asin(r[0][2])
            thetaX = atan2(-r[1][2], r[2][2])
            thetaZ = atan2(-r[0][1], r[0][0])
        else:   # r[0][2] = -1
            # not a unique solution: thetaZ - thetaX = atan2(r[1][0], r[1][1])
            thetaY = -pi/2
            thetaX = -atan2(r[1][0], r[1][1])
            thetaZ = 0
    else:   # r[0][2] = +1
        # not a unique solution: thetaZ + thetaX = atan2(r[1][0], r[1][1])
        thetaY = pi/2
        thetaX = atan2(r[1][0], r[1][1])
        thetaZ = 0
    #
    omega = thetaX
    phi = thetaY
    kappa = thetaZ
    return (omega, phi, kappa)


# ==================================================================================================
def matrix_world_to_ypr(matrix_world: Matrix) -> Tuple[float, float, float]:
    """Extract Yaw, Pitch, Roll angles from a worldspace transformation matrix.

    Pitch and Roll are CCW rotation along the X, Y axis respectively. Yaw is a CW rotation along the Z axis.
    The order of application is RPY = YXZ (R=Rz*Rx*Ry).

    https://www.geometrictools.com/Documentation/EulerAngles.pdf
    https://www.agisoft.com/forum/index.php?topic=8187.msg39193#msg39193
    https://www.agisoft.com/forum/index.php?topic=5100.msg25350#msg25350

    Arguments:
        matrix_world {Matrix} -- worldspace transformation matrix.

    Returns:
        Tuple[float, float, float] -- Yaw, Pitch, Roll angles in radians.
    """
    r = matrix_world
    if r[2][1] < 1:
        if r[2][1] > -1:
            thetaX = asin(r[2][1])
            thetaZ = atan2(-r[0][1], r[1][1])
            thetaY = atan2(-r[2][0], r[2][2])
        else:   # r[2][1] =−1
            # not a unique  solution: thetaY - thetaZ = atan2(r[0][2] , r[0][0])
            thetaX = -pi/2
            thetaZ = -atan2(r[0][2], r[0][0])
            thetaY = 0
    else:   # r[2][1] = +1
        # not a unique solution: thetaY + thetaZ = atan2(r[0][2], r[0][0])
        thetaX = pi/2
        thetaZ = atan2(r[0][2], r[0][0])
        thetaY = 0
    #
    pitch = thetaX
    roll = thetaY
    yaw = -thetaZ
    return (yaw, pitch, roll)

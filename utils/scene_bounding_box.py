
import logging
from typing import Tuple

import bpy
from mathutils import Vector

from .object import SFMFLOW_COLLECTIONS, get_objs

logger = logging.getLogger(__name__)


class SceneBoundingBox():
    """Scene bounding box, build a bounding box that includes all objects except the excluded ones."""

    ################################################################################################
    # Properties
    #

    # ==============================================================================================
    @property
    def width(self):
        """Scene's bounding box width."""
        return self.x_max - self.x_min

    # ==============================================================================================
    @property
    def depth(self):
        """Scene's bounding box depth."""
        return self.y_max - self.y_min

    # ==============================================================================================
    @property
    def height(self):
        """Scene's bounding box height."""
        return self.z_max - self.z_min

    # ==============================================================================================
    @property
    def floor_center(self):
        """Scene's bounding center on lower bbox plane."""
        return Vector((self.center[0], self.center[1], self.z_min))

    ################################################################################################
    # Constructor
    #

    # ==============================================================================================
    def __init__(self, scene: bpy.types.Scene, exclude_collections: Tuple[str] = SFMFLOW_COLLECTIONS):
        self.scene = scene
        self.exclude_collections = exclude_collections
        #
        self.center = Vector()       # type: Vector
        self.x_min = float("inf")    # type: float
        self.x_max = float("-inf")   # type: float
        self.y_min = float("inf")    # type: float
        self.y_max = float("-inf")   # type: float
        self.z_min = float("inf")    # type: float
        self.z_max = float("-inf")   # type: float
        #
        self.compute()

    ################################################################################################
    # Methods
    #

    # ==============================================================================================
    def compute(self):
        """Compute the scene bounding box values."""
        objs = get_objs(self.scene, exclude_collections=self.exclude_collections, mesh_only=True)
        logger.debug("Found %i objects in scene %s", len(objs), self.scene.name)
        for obj in objs:
            obb = obj.bound_box
            for i in range(8):
                p = obj.matrix_world @ Vector(obb[i])
                self.x_min = min(self.x_min, p[0])
                self.x_max = max(self.x_max, p[0])
                self.y_min = min(self.y_min, p[1])
                self.y_max = max(self.y_max, p[1])
                self.z_min = min(self.z_min, p[2])
                self.z_max = max(self.z_max, p[2])
        if objs:
            self.center = Vector(((self.x_max + self.x_min) / 2,
                                  (self.y_max + self.y_min) / 2,
                                  (self.z_max + self.z_min) / 2))
        logger.debug(str(self))

    # ==============================================================================================
    def get_min_vector(self):
        """Get minimum axis."""
        return Vector((self.x_min, self.y_min, self.z_min))

    # ==============================================================================================
    def get_max_vector(self):
        """Get maximum axis."""
        return Vector((self.x_max, self.y_max, self.z_max))

    ################################################################################################
    # Builtin methods
    #

    # ==============================================================================================
    def __str__(self):
        return "Scene bbox values: X=({:.3f}, {:.3f}), Y=({:.3f}, {:.3f}), Z=({:.3f}, {:.3f}), Center={}".format(
            self.x_min, self.x_max, self.y_min, self.y_max, self.z_min, self.z_max, self.center)

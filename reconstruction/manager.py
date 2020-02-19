
import logging
from typing import List, Optional

import bpy
from mathutils import Vector
from mathutils.kdtree import KDTree

from .components import ReconModel
from .reconstruction_base import ReconstructionBase

logger = logging.getLogger(__name__)


class ReconstructionsManager:
    """Class to handle global access to the 3D reconstruction imported by the user."""

    reconstructions = []   # type: List[ReconstructionBase]
    gt_points = None       # type: List[Vector]
    gt_kdtree = None       # type: KDTree

    ################################################################################################
    # Methods
    #

    # ==============================================================================================
    @classmethod
    def add_reconstruction(cls, reconstruction: ReconstructionBase) -> None:
        """Add a reconstruction to the globally available ones.

        Arguments:
            reconstruction {ReconstructionBase} -- 3D reconstruction
        """
        cls.unload_deleted()
        #
        cls.reconstructions.append(reconstruction)

    # ==============================================================================================
    @classmethod
    def set_gt_points(cls, gt_points: List[Vector] = None) -> None:
        """Set the ground truth point cloud. Automatically creates the KDTree to speed up point cloud operations.

        Keyword Arguments:
            gt_points {List[Vector]} -- ground truth point cloud. If {None} both the point cloud
                                        and the KDTree are cleared. (default: {None})
        """
        cls.unload_deleted()
        #
        cls.gt_points = gt_points
        if gt_points is not None:
            # build KDTree for target point cloud to speed up the nearest neighbor search
            cls.gt_kdtree = KDTree(len(gt_points))
            for i, v in enumerate(gt_points):
                cls.gt_kdtree.insert(v, i)
            cls.gt_kdtree.balance()

    # ==============================================================================================
    @classmethod
    def remove_all(cls) -> None:
        """Remove all the reconstructions and release resources."""
        while len(cls.reconstructions) > 0:
            recon = cls.reconstructions.pop()
            recon.free()
            del recon

    # ==============================================================================================
    @classmethod
    def remove(cls, reconstruction: ReconstructionBase) -> None:
        """Remove a given reconstruction from the loaded ones and release resources.

        Arguments:
            reconstruction {ReconstructionBase} -- the 3D reconstruction to be removed
        """
        i = cls.reconstructions.index(reconstruction)
        recon = cls.reconstructions.pop(i)
        recon.free()
        del recon

    # ==============================================================================================
    @classmethod
    def free(cls) -> None:
        """Prepare for destruction and release resources."""
        ReconstructionsManager.remove_all()
        del ReconstructionsManager.gt_kdtree

    # ==============================================================================================
    @classmethod
    def get_model_by_uuid(cls, uuid: str) -> Optional[ReconModel]:
        """Get a reconstruction model given its UUID.

        Arguments:
            uuid {str} -- unique identifier of the reconstructed model to recover

        Returns:
            Tuple[ReconModel, List[Vector]] -- reconstructed model and ground truth geometry points
        """
        cls.unload_deleted()
        #
        for recon in cls.reconstructions:
            for model in recon.models:
                if model.uuid == uuid:
                    return model
        return None

    # ==============================================================================================
    @classmethod
    def unload_deleted(cls) -> None:
        """Unload reconstructions and reconstruction models that are no longer in use."""
        to_delete = []
        for recon in cls.reconstructions:
            if recon.unload_deleted():
                to_delete.append(recon)
        for recon in to_delete:
            logger.debug("Removing reconstruction '%s' because has no models left", recon.name)
            cls.remove(recon)

    ################################################################################################
    # Backup and restore
    #

    # ==============================================================================================
    @classmethod
    def backup(cls) -> None:
        """Backup current reconstructions to a temporary property.
        This is used for development purpose to avoid reconstructions reset on add-on reload.
        @see also restore()
        """
        cls.unload_deleted()
        #
        bpy.types.Scene.sfmflow_reconstructions_backup = (cls.reconstructions, cls.gt_points)
        logger.debug("Loaded reconstructions temporary saved to 'bpy.types.Scene.sfmflow_reconstructions_backup'")

    # ==============================================================================================
    @classmethod
    def restore(cls) -> None:
        """Restore reconstructions from a temporary property (if exists).
        This is used for development purpose to avoid property reset on add-on reload.
        @see also backup()
        """
        cls.unload_deleted()
        #
        if hasattr(bpy.types.Scene, "sfmflow_reconstructions_backup"):
            cls.reconstructions = bpy.types.Scene.sfmflow_reconstructions_backup[0]
            cls.set_gt_points(bpy.types.Scene.sfmflow_reconstructions_backup[1])  # set gt points and rebuild kdtree


import logging
from typing import List

import bpy
from mathutils import Vector
from sfm_flow.reconstruction import ReconstructionsManager
from sfm_flow.utils import SFMFLOW_COLLECTIONS, get_objs, sample_points_on_mesh

logger = logging.getLogger(__name__)


class SFMFLOW_OT_sample_geometry_gt(bpy.types.Operator):
    """Sample the geometry ground truth."""
    bl_idname = "sfmflow.sample_geometry_gt"
    bl_label = "Sample geometry gt"
    bl_options = {'REGISTER'}   # UNDO/REDO currently unsupported

    ################################################################################################
    # Behavior
    #

    # ==============================================================================================
    @classmethod
    def poll(cls, context: bpy.types.Context) -> bool:   # pylint: disable=unused-argument
        """Panel's enabling condition.
        The operator is enabled only if a 3D reconstruction is loaded.

        Arguments:
            context {bpy.types.Context} -- poll context

        Returns:
            bool -- True to enable, False to disable
        """
        return ReconstructionsManager.gt_points is not None

    # ==============================================================================================
    def execute(self, context: bpy.types.Context) -> set:
        """Sample ground truth point cloud.

        Returns:
            set -- {'FINISHED'}
        """
        gt_points = SFMFLOW_OT_sample_geometry_gt.sample_geometry_gt_points(context.scene)
        ReconstructionsManager.set_gt_points(gt_points)
        #
        msg = f"Sampled {len(gt_points)} points"
        logger.info(msg)
        self.report({'INFO'}, msg)
        return {'FINISHED'}

    ################################################################################################
    # Helper methods
    #

    # ==============================================================================================
    @staticmethod
    def sample_geometry_gt_points(scene: bpy.types.Scene) -> List[Vector]:
        """Sample ground truth point cloud on all objects that are not part of the `SFMFLOW_*` collections.

        Arguments:
            scene {bpy.types.Scene} -- scene to sample

        Returns:
            List[Vector] -- ground truth point cloud
        """
        gt_objs = get_objs(scene, exclude_collections=SFMFLOW_COLLECTIONS)
        gt_points = sample_points_on_mesh(gt_objs)
        # self._show_sampled_points(gt_points)
        return gt_points

    # ==============================================================================================
    @staticmethod
    def _show_sampled_points(points: List[Vector]) -> None:
        """Show a sampled point cloud. Only for debug!

        Arguments:
            points {List[Vector]} -- point cloud
        """
        mesh = bpy.data.meshes.new("sampled_data")
        obj = bpy.data.objects.new("sampled", mesh)
        bpy.context.scene.collection.objects.link(obj)
        mesh.from_pydata(points, [], [])
        mesh.update()

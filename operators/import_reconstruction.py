
import logging
import os
from pathlib import Path
from typing import List

import bpy
from bpy_extras.io_utils import ImportHelper
from mathutils import Vector
from sfm_flow.operators.sample_geometry_gt import SFMFLOW_OT_sample_geometry_gt
from sfm_flow.reconstruction import ReconstructionBase, ReconstructionsManager

logger = logging.getLogger(__name__)


class SFMFLOW_OT_import_reconstruction(bpy.types.Operator, ImportHelper):
    """Import an SfM 3D reconstruction form reconstruction file"""
    bl_idname = "sfmflow.import_reconstruction"
    bl_label = "Import reconstruction"
    bl_options = {'REGISTER'}   # UNDO/REDO currently unsupported

    ################################################################################################
    # Properties
    #

    # ==============================================================================================
    # file extension filter
    filter_glob: bpy.props.StringProperty(
        default="",
        options={'HIDDEN'}
    )

    ################################################################################################
    # Behavior
    #

    # ==============================================================================================
    def invoke(self, context: bpy.types.Context, event: bpy.types.Event) -> set:  # pylint: disable=unused-argument
        """Init operator when invoked.
        Start file selector in the reconstruction folder if possible.

        Arguments:
            context {bpy.types.Context} -- invoke context
            event {bpy.types.Event} -- invoke event

        Returns:
            set -- {‘RUNNING_MODAL’}
        """
        properties = context.scene.sfmflow
        recon_path = bpy.path.abspath(properties.reconstruction_path)
        filepath = recon_path if os.path.isdir(recon_path) else os.path.dirname(bpy.data.filepath)
        #
        filter_glob = ReconstructionBase.get_supported_files_filter()
        self.filter_glob = filter_glob
        filepath = os.path.join(filepath, filter_glob)
        #
        self.filepath = filepath
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    # ==============================================================================================
    def execute(self, context: bpy.types.Context) -> set:
        """Import a 3D reconstruction.

        Returns:
            set -- {'FINISHED'}
        """
        logger.info("Importing reconstruction form file: %s", self.filepath)
        i_map = ReconstructionBase.get_supported_files()
        path = Path(self.filepath)
        ext = ''.join(path.suffixes)
        recon = i_map[ext](path.stem, self.filepath)   # import the reconstruction file
        #
        # sample ground truth
        if ReconstructionsManager.gt_points is None:
            gt_points = SFMFLOW_OT_sample_geometry_gt.sample_geometry_gt_points(context.scene)
            ReconstructionsManager.set_gt_points(gt_points)
        #
        # store the reconstruction
        ReconstructionsManager.add_reconstruction(recon)
        recon.show()
        #
        if len(recon.models) == 1:   # if only one model loaded set it as active object in the viewport
            recon.models[0].set_active(context)
        #
        msg = f"Reconstruction `{recon.name}` imported"
        logger.info(msg)
        self.report({'INFO'}, msg)
        return {'FINISHED'}

    # ==============================================================================================
    @staticmethod
    def show_sampled_points(points: List[Vector]) -> None:
        """Show a sampled point cloud. NOTE only for debug!

        Arguments:
            points {List[Vector]} -- point cloud
        """
        mesh = bpy.data.meshes.new("sampled_data")
        obj = bpy.data.objects.new("sampled", mesh)
        bpy.context.scene.collection.objects.link(obj)
        #
        mesh.from_pydata(points, [], [])
        mesh.update()

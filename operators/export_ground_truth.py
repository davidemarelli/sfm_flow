
import logging
import os

import bpy

from ..utils import get_objs

logger = logging.getLogger(__name__)


class SFMFLOW_OT_export_ground_truth(bpy.types.Operator):
    """Save ground truth .obj file of the scene's geometry"""
    bl_idname = "sfmflow.export_ground_truth"
    bl_label = "Export ground truth geometry"

    ################################################################################################
    # Properties
    #

    # ==============================================================================================
    export_type: bpy.props.EnumProperty(
        name="Export type",
        description="Geometry ground truth export type",
        items=[
            ("exporttype.all", "All",
             "Export all meshes not part of the `SfM_Environment` or 'SfM_Reconstructions' collections"),
            ("exporttype.selected", "Selected only", "Export selected objects only"),
        ],
        default="exporttype.all",
        options={'SKIP_SAVE'}
    )

    # ==============================================================================================
    export_folder: bpy.props.StringProperty(
        name="Export folder",
        description="Geometry ground truth export folder",
        subtype='DIR_PATH',
        options={'SKIP_SAVE'}
    )

    ################################################################################################
    # Layout
    #

    def draw(self, context: bpy.types.Context):   # pylint: disable=unused-argument
        """Operator panel layout"""
        layout = self.layout
        layout.prop(self, "export_type")
        layout.prop(self, "export_folder")

    ################################################################################################
    # Behavior
    #

    # ==============================================================================================
    def invoke(self, context: bpy.types.Context, event: bpy.types.Event) -> set:  # pylint: disable=unused-argument
        """Init operator when invoked.

        Arguments:
            context {bpy.types.Context} -- invoke context
            event {bpy.types.Event} -- invoke event

        Returns:
            set -- enum set in {‘RUNNING_MODAL’, ‘CANCELLED’, ‘FINISHED’, ‘PASS_THROUGH’, ‘INTERFACE’}
        """
        if bpy.data.is_saved:
            if bpy.data.is_dirty:
                # unsaved changes are present
                self.report({'WARNING'}, "Unsaved changes found, check and UNDO or SAVE changes before export")
                return {'CANCELLED'}

            self.export_folder = context.scene.render.filepath

            wm = context.window_manager
            return wm.invoke_props_dialog(self)
        else:
            self.report({'WARNING'}, "Save project before export")
            return {'CANCELLED'}

    # ==============================================================================================
    def execute(self, context: bpy.types.Context) -> set:
        """Export geometry ground truth based on user's settings.

        Returns:
            set -- {'FINISHED'}
        """
        if self.export_type == "exporttype.all":
            objs = get_objs(context.scene, exclude_collections=(
                "SfM_Environment", "SfM_Reconstructions"), mesh_only=True)
            bpy.ops.object.select_all(action='DESELECT')
            for o in objs:
                o.select_set(True)
        gtFilePath = os.path.join(bpy.path.abspath(self.export_folder), "ground_truth.obj")
        SFMFLOW_OT_export_ground_truth.export_selection_as_obj(gtFilePath)
        return {'FINISHED'}

    ################################################################################################
    # Helper methods
    #

    # ==============================================================================================
    @staticmethod
    def export_selection_as_obj(objFilePath: str) -> None:
        """Export currently selected objects as .obj files.

        Arguments:
            objFilePath {str} -- path to obj file
        """
        logger.info("SfM - Exporting ground truth")
        #
        os.makedirs(os.path.dirname(objFilePath), exist_ok=True)
        bpy.ops.export_scene.obj(
            filepath=objFilePath,
            check_existing=True,
            axis_forward='Y',                 # blender reference system
            axis_up='Z',                      # blender reference system
            filter_glob="*.obj;*.mtl",
            use_selection=True,               # export only currently selected
            use_animation=False,
            use_mesh_modifiers=True,
            use_edges=True,
            use_smooth_groups=False,
            use_smooth_groups_bitflags=False,
            use_normals=True,
            use_uvs=True,
            use_materials=True,
            use_triangles=False,
            use_nurbs=False,
            use_vertex_groups=False,
            use_blen_objects=True,
            group_by_object=False,
            group_by_material=False,
            keep_vertex_order=False,
            global_scale=1,
            path_mode='AUTO'
        )
        logger.info("SfM - Ground truth exported")

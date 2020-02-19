
import logging

import bpy
from sfm_flow.reconstruction import ReconstructionsManager
from sfm_flow.utils import is_active_object_reconstruction

logger = logging.getLogger(__name__)


class SFMFLOW_OT_reconstruction_filter(bpy.types.Operator):
    """Filter a reconstructed point cloud"""
    bl_idname = "sfmflow.reconstruction_filter"
    bl_label = "Filter selected point cloud"
    bl_options = {'REGISTER'}

    ################################################################################################
    # Properties
    #

    # ==============================================================================================
    filter_distance_threshold: bpy.props.FloatProperty(
        name="Distance treshold",
        description="Distance treshold for point cloud filtering",
        default=1.,
        min=0.0,
        soft_max=10.0,
        subtype='DISTANCE',
        options={'SKIP_SAVE'}
    )

    ################################################################################################
    # Layout
    #

    def draw(self, context: bpy.types.Context):   # pylint: disable=unused-argument
        """Operator panel layout"""
        layout = self.layout
        layout.prop(self, "filter_distance_threshold")

    ################################################################################################
    # Behavior
    #

    # ==============================================================================================
    @classmethod
    def poll(cls, context: bpy.types.Context) -> bool:
        """Panel's enabling condition.
        The operator is enabled only if a 3D reconstruction is selected.

        Arguments:
            context {bpy.types.Context} -- poll context

        Returns:
            bool -- True to enable, False to disable
        """
        return is_active_object_reconstruction(context)

    # ==============================================================================================
    def invoke(self, context: bpy.types.Context, event: bpy.types.Event) -> set:  # pylint: disable=unused-argument
        """Init operator when invoked.

        Arguments:
            context {bpy.types.Context} -- invoke context
            event {bpy.types.Event} -- invoke event

        Returns:
            set -- enum set in {‘RUNNING_MODAL’, ‘CANCELLED’, ‘FINISHED’, ‘PASS_THROUGH’, ‘INTERFACE’}
        """
        wm = context.window_manager
        return wm.invoke_props_dialog(self)

    # ==============================================================================================
    def execute(self, context: bpy.types.Context) -> set:
        """Filter the reconstructed point cloud.

        Returns:
            set -- {'FINISHED'}
        """
        obj = context.view_layer.objects.active
        model = ReconstructionsManager.get_model_by_uuid(obj['sfmflow_model_uuid'])
        model.filter_model(ReconstructionsManager.gt_kdtree, self.filter_distance_threshold)
        return {'FINISHED'}


#
#
#
#


class SFMFLOW_OT_reconstruction_filter_clear(bpy.types.Operator):
    """Clear the point cloud filtering"""
    bl_idname = "sfmflow.reconstruction_filter_clear"
    bl_label = "Clear a reconstruction filtering"
    bl_options = {'REGISTER'}

    ################################################################################################
    # Behavior
    #

    # ==============================================================================================
    @classmethod
    def poll(cls, context: bpy.types.Context) -> bool:
        """Panel's enabling condition.
        The operator is enabled only if a filtered 3D reconstruction is selected.

        Arguments:
            context {bpy.types.Context} -- poll context

        Returns:
            bool -- True to enable, False to disable
        """
        if is_active_object_reconstruction(context):
            # the selected object is a UI control for a reconstruction
            model = ReconstructionsManager.get_model_by_uuid(context.view_layer.objects.active['sfmflow_model_uuid'])
            return model.has_filter_model()
        return False

    # ==============================================================================================
    def execute(self, context: bpy.types.Context) -> set:
        """Clear the point cloud filtering, restore the full cloud.

        Returns:
            set -- {'FINISHED'}
        """
        obj = context.view_layer.objects.active
        model = ReconstructionsManager.get_model_by_uuid(obj['sfmflow_model_uuid'])
        model.filter_model_clear()
        return {'FINISHED'}

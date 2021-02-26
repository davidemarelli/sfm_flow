
import logging

import bpy

from ..utils.object import get_average_z_coord

logger = logging.getLogger(__name__)


class SFMFLOW_OT_set_average_ground_altitude(bpy.types.Operator):
    """Compute and set the average ground altitude of the current scene (average Z coordinate of the vertices)"""
    bl_idname = "sfmflow.set_average_ground_altitude"
    bl_label = "Get average scene altitude"
    bl_options = {'REGISTER'}

    z_average = 0.

    ################################################################################################
    # Layout
    #

    def draw(self, context: bpy.types.Context):   # pylint: disable=unused-argument
        """Operator layout"""
        layout = self.layout
        row = layout.row(align=True)
        row.label(text="Average scene altitude (Z): ")
        row.label(text="{:.3f}".format(SFMFLOW_OT_set_average_ground_altitude.z_average))

    ################################################################################################
    # Behavior
    #

    # ==============================================================================================
    def invoke(self, context: bpy.types.Context, event: bpy.types.Event) -> set:  # pylint: disable=unused-argument
        """Init operator when invoked, compute the average ground altitude of the current scene.

        Arguments:
            context {bpy.types.Context} -- invoke context
            event {bpy.types.Event} -- invoke event

        Returns:
            set -- enum set in {‘RUNNING_MODAL’, ‘CANCELLED’, ‘FINISHED’, ‘PASS_THROUGH’, ‘INTERFACE’}
        """
        logger.info("Computing average scene Z coordinate...")
        scene = context.scene
        z_average = get_average_z_coord(scene)
        SFMFLOW_OT_set_average_ground_altitude.z_average = z_average
        logger.debug("Average scene altitude (Z): %f", z_average)
        #
        wm = context.window_manager
        return wm.invoke_props_dialog(self)

    # ==============================================================================================
    def execute(self, context: bpy.types.Context) -> set:
        """Set the average ground altitude.

        Arguments:
            context {bpy.types.Context} -- execution context

        Returns:
            set -- {'FINISHED'}
        """
        context.scene.sfmflow.scene_ground_average_z = SFMFLOW_OT_set_average_ground_altitude.z_average
        logger.info("Average scene ground altitude set to: %f", SFMFLOW_OT_set_average_ground_altitude.z_average)
        return {'FINISHED'}


import logging

import bpy
from sfm_flow.utils.animation import has_keyframes, randomize_transform_keyframes

logger = logging.getLogger(__name__)


class SFMFLOW_OT_randomize_animation(bpy.types.Operator):
    """Randomize the location of the keyframes of the current object animation"""
    bl_idname = "sfmflow.randomize_animation"
    bl_label = "Randomize animation"
    bl_options = {'REGISTER', 'UNDO'}

    ################################################################################################
    # Properties
    #

    # ==============================================================================================
    # min, max limits on each axis
    limits_min: bpy.props.FloatVectorProperty(
        size=3,
        default=(-.5, -.5, -.5),
        max=0.,
        precision=3,
        subtype='XYZ_LENGTH',
        options={'SKIP_SAVE'}
    )

    limits_max: bpy.props.FloatVectorProperty(
        size=3,
        default=(.5, .5, .5),
        min=0.,
        precision=3,
        subtype='XYZ_LENGTH',
        options={'SKIP_SAVE'}
    )

    ################################################################################################
    # Layout
    #

    def draw(self, context: bpy.types.Context):   # pylint: disable=unused-argument
        """Operator layout"""
        layout = self.layout
        layout.label(text="Randomization limits")
        row = layout.row()
        col = row.column()
        col.label(text="Min")
        col.prop(self, "limits_min", text="")
        col = row.column()
        col.label(text="Max")
        col.prop(self, "limits_max", text="")

    ################################################################################################
    # Behavior
    #

    # ==============================================================================================
    @classmethod
    def poll(cls, context: bpy.types.Context) -> bool:
        """Operator's enabling condition.
        The operator is enabled only if an object with location keyframes is selected and active.

        Arguments:
            context {bpy.types.Context} -- poll context

        Returns:
            bool -- True to enable, False to disable
        """
        return has_keyframes(context.active_object, 'location')

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
        """Randomize the object location at the existing keypoints.
        Randomization range is based on user's settings.

        Returns:
            set -- {'FINISHED'}
        """
        logger.info("Randomizing animation...")

        if not has_keyframes(context.active_object, 'location'):
            msg = "No object with 'location' keyframes selected!"
            logger.error(msg)
            self.report({'ERROR'}, msg)
            return {'CANCELLED'}
        #
        obj = context.active_object
        randomize_transform_keyframes(obj, [self.limits_min, self.limits_max])
        context.view_layer.update()
        #
        logger.info("Animation of obj '%s' randomized. Limits: min=%s, max=%s.",
                    obj.name, self.limits_min, self.limits_max)
        return {'FINISHED'}

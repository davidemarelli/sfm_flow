"""Render cameras operators."""

import bpy


class SFMFLOW_OT_render_camera_slot_add(bpy.types.Operator):
    """Add a slot for a render camera."""
    bl_idname = "sfmflow.render_camera_slot_add"
    bl_label = "Add a new render camera slot"

    ################################################################################################
    # Behavior
    #

    def execute(self, context: bpy.types.Context) -> set:
        """Operator execution. Add a new slot for a render camera.

        Arguments:
            context {bpy.types.Context} -- current context

        Returns:
            set -- {'FINISHED'}
        """
        properties = context.scene.sfmflow
        properties.render_cameras.add()
        properties.render_cameras_idx = len(properties.render_cameras) - 1

        return {'FINISHED'}


#
#
#
#


class SFMFLOW_OT_render_camera_slot_remove(bpy.types.Operator):
    """Remove the selected render camera slot."""
    bl_idname = "sfmflow.render_camera_slot_remove"
    bl_label = "Remove the selected render camera slot"

    ################################################################################################
    # Behavior
    #

    # ==============================================================================================
    @classmethod
    def poll(cls, context: bpy.types.Context) -> bool:
        """Operator's enabling condition.
        The operator is enabled only if a render camera slot is selected.

        Arguments:
            context {bpy.types.Context} -- poll context

        Returns:
            bool -- True to enable, False to disable
        """
        properties = context.scene.sfmflow
        return properties.render_cameras_idx >= 0

    # ==============================================================================================
    def execute(self, context: bpy.types.Context) -> set:
        """Operator execution. Remove the selected render camera slot.

        Arguments:
            context {bpy.types.Context} -- current context

        Returns:
            set -- {'FINISHED'}
        """
        properties = context.scene.sfmflow
        properties.render_cameras.remove(properties.render_cameras_idx)
        properties.render_cameras_idx -= 1
        return {'FINISHED'}

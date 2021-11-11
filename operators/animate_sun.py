
import logging
from random import shuffle

import bpy
from mathutils import Vector
from sfm_flow.utils import SceneBoundingBox
from sfm_flow.utils.animation import is_keyframe, sun_animation_points

from .init_scene import SFMFLOW_OT_init_scene

logger = logging.getLogger(__name__)


class SFMFLOW_OT_animate_sun(bpy.types.Operator):
    """Animate the sun lamp path for SfM dataset generation"""
    bl_idname = "sfmflow.animate_sun"
    bl_label = "Animate sun"
    bl_options = {'REGISTER', 'UNDO'}

    ################################################################################################
    # Properties
    #

    # ==============================================================================================
    north_direction: bpy.props.EnumProperty(
        name="North direction",
        description="Axis direction that is pointing to north",
        items=(
            ("north.pos_x", "+X", "North X+"),
            ("north.neg_x", "−X", "North -X"),
            ("north.pos_y", "+Y", "North Y+"),
            ("north.neg_y", "−Y", "North -Y"),
        ),
        default="north.pos_y"
    )

    # ==============================================================================================
    start_frame: bpy.props.IntProperty(
        name="Start",
        description="Animation start frame",
        default=1,
        min=1,
        max=1000,
        soft_min=1,
        soft_max=500,
        step=1,
        subtype='UNSIGNED',
        options={'SKIP_SAVE'}
    )

    # ==============================================================================================
    end_frame: bpy.props.IntProperty(
        name="End",
        description="Animation end frame",
        default=250,
        min=1,
        max=1000,
        soft_min=1,
        soft_max=500,
        step=1,
        subtype='UNSIGNED',
        options={'SKIP_SAVE'}
    )

    # ==============================================================================================
    randomize_pos: bpy.props.BoolProperty(
        name="Randomize position",
        description="Randomize sun position",
        default=True,
        options={'SKIP_SAVE'}
    )

    # ==============================================================================================
    overwrite_existing_animation: bpy.props.BoolProperty(
        name="Overwrite existing animation",
        description="Overwrite existing animation keyframes (if any)",
        default=True,
        options={'SKIP_SAVE'}
    )

    ################################################################################################
    # Layout
    #

    def draw(self, context: bpy.types.Context):
        """Operator panel layout"""
        layout = self.layout
        if ("SunDriver" in context.scene.objects) and (context.scene.objects["SunDriver"].animation_data is not None):
            layout.prop(self, "overwrite_existing_animation")
        row = layout.split(factor=0.45, align=True)
        row.label(text="Animation frame range")
        row = row.split(factor=0.5, align=True)
        row.prop(self, "start_frame")
        row.prop(self, "end_frame")
        layout.prop(self, "randomize_pos")
        row = layout.split(factor=0.45, align=True)
        row.label(text="North direction")
        row.row().prop(self, "north_direction", expand=True)

    ################################################################################################
    # Behavior
    #

    # ==============================================================================================
    @classmethod
    def poll(cls, context: bpy.types.Context) -> bool:
        """Panel's enabling condition.
        The operator is enabled only if the SunDriver object exists.

        Arguments:
            context {bpy.types.Context} -- poll context

        Returns:
            bool -- True to enable, False to disable
        """
        return "SunDriver" in context.scene.objects

    # ==============================================================================================
    def invoke(self, context: bpy.types.Context, event: bpy.types.Event) -> set:  # pylint: disable=unused-argument
        """Init operator when invoked.

        Arguments:
            context {bpy.types.Context} -- invoke context
            event {bpy.types.Event} -- invoke event

        Returns:
            set -- enum set in {‘RUNNING_MODAL’, ‘CANCELLED’, ‘FINISHED’, ‘PASS_THROUGH’, ‘INTERFACE’}
        """
        self.start_frame = context.scene.frame_start
        self.end_frame = context.scene.frame_end
        #
        wm = context.window_manager
        return wm.invoke_props_dialog(self)

    # ==============================================================================================
    def execute(self, context: bpy.types.Context) -> set:
        """Animate the sun lamp based on user's settings.

        Returns:
            set -- {'FINISHED'}
        """
        logger.info("Animating sun...")

        scene = context.scene
        bbox = SceneBoundingBox(scene)
        animation_length = self.end_frame - self.start_frame
        #
        if self.north_direction == "north.pos_x":
            north_direction = Vector((1, 0, 0))
        elif self.north_direction == "north.neg_x":
            north_direction = Vector((-1, 0, 0))
        elif self.north_direction == "north.neg_y":
            north_direction = Vector((0, -1, 0))
        else:  # "north.pos_y"
            north_direction = Vector((0, 1, 0))
        #
        points = sun_animation_points(Vector((0, 0, -1)), north_direction, scene_bbox=bbox,
                                      radius=1, points_count=animation_length)
        #
        if self.randomize_pos:
            shuffle(points)
        #
        no_rotation = bbox.floor_center
        sun = scene.objects["SunDriver"]
        sun.rotation_mode = 'QUATERNION'
        for i, p in enumerate(points):
            frame_number = self.start_frame+i
            if self.overwrite_existing_animation or not is_keyframe(sun, frame_number):
                rot_diff = no_rotation.rotation_difference(p)
                sun.rotation_quaternion = rot_diff
                sun.keyframe_insert("rotation_quaternion", frame=frame_number)
        #
        logger.info("Sun '%s' animated (length=%i)", sun.name, len(points))
        return {'FINISHED'}


#
#
#
#


class SFMFLOW_OT_animate_sun_clear(bpy.types.Operator):
    """Clear the animation of the sun lamp"""
    bl_idname = "sfmflow.animate_sun_clear"
    bl_label = "Clear sun animation"
    bl_options = {'REGISTER', 'UNDO'}

    ################################################################################################
    # Behavior
    #

    # ==============================================================================================
    @classmethod
    def poll(cls, context: bpy.types.Context) -> bool:
        """Panel's enabling condition.
        The operator is enabled only if the SunDriver object exists and has an animation path.

        Arguments:
            context {bpy.types.Context} -- poll context

        Returns:
            bool -- True to enable, False to disable
        """
        return (("SunDriver" in context.scene.objects) and
                (context.scene.objects["SunDriver"].animation_data is not None))

    # ==============================================================================================
    def execute(self, context: bpy.types.Context) -> set:
        """Clear the sun lamp animation path.

        Raises:
            NotImplementedError: for animation types not yet implemented

        Returns:
            set -- {'FINISHED'}
        """
        sun = context.scene.objects["SunDriver"]
        sun.animation_data_clear()
        sun.rotation_mode = "XYZ"
        sun.rotation_euler = SFMFLOW_OT_init_scene.DEFAULT_SUN_ROTATION
        #
        logger.info("Cleared animation for sun '%s'.", sun.name)
        return {'FINISHED'}

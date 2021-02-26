
import logging
from math import radians

import bpy
from mathutils import Vector

from ..utils import SceneBoundingBox, euclidean_distance
from ..utils.animation import (get_last_keyframe, get_track_to_constraint_target,
                               sample_points_on_circle, sample_points_on_helix,
                               sample_points_on_hemisphere, set_camera_focus_to_intersection,
                               set_camera_target)
from ..utils.camera import (get_camera_right, get_camera_up, get_ground_sample_distance,
                            is_active_object_camera)

logger = logging.getLogger(__name__)


class SFMFLOW_OT_animate_camera(bpy.types.Operator):
    """Animate the selected camera for SfM dataset generation"""
    bl_idname = "sfmflow.animate_camera"
    bl_label = "Animate selected camera"
    bl_options = {'REGISTER', 'UNDO'}

    # scene bounding box, set on invoke and used in execute
    _scene_bbox = None   # type: SceneBoundingBox

    ################################################################################################
    # Properties
    #

    # ==============================================================================================
    animation_type: bpy.props.EnumProperty(
        name="Animation type",
        description="Render camera animation type",
        items=[
            ("animtype.helix", "Helix", "Helix around objects."),
            ("animtype.hemisphere", "Hemisphere",
             "Sample positions on an hemisphere. NOTE: start position not preserved"),
            ("animtype.circular", "Circular", "Animate a singe circle around the center of the scene"),
            ("animtype.circular_up", "Circular - UP",
             "Animate multiple circles, the camera positions are shared between circles but the target"
             " position increases its height until the scene top is reached."),
            ("animtype.aerial_grid", "Aerial grid", "Acquire images with a regular grid pattern."),
        ],
        default="animtype.helix",
        options={'SKIP_SAVE'}
    )

    # ==============================================================================================
    images_count: bpy.props.IntProperty(
        name="Animation length",
        description="Number of desired camera poses/images",
        default=100,
        min=1,
        max=1000,
        soft_min=1,
        soft_max=500,
        step=1,
        subtype='UNSIGNED',
        options={'SKIP_SAVE'}
    )

    # ==============================================================================================
    # animation height (used only for `helix` and `circular_up`)
    animation_height: bpy.props.FloatProperty(
        name="Animation height",
        description="Height of the camera animation",
        min=0.0,
        soft_min=1.,
        subtype='UNSIGNED',
        unit='LENGTH',
        options={'SKIP_SAVE'}
    )

    # ==============================================================================================
    # animation turns count (used only for `helix` and `circular_up`)
    animation_turns: bpy.props.IntProperty(
        name="Animation turns",
        description="Number of desired camera animation turns",
        min=1,
        max=1000,
        soft_max=25,
        step=1,
        subtype='UNSIGNED',
        options={'SKIP_SAVE'}
    )

    # ==============================================================================================
    # animation poses randomization flag
    randomize_camera_pose: bpy.props.BoolProperty(
        name="Randomize position ±5%",
        description="Randomize camera position about ±5%",
        default=True,
        options={'SKIP_SAVE'}
    )

    # ==============================================================================================
    overwrite_existing_animation: bpy.props.BoolProperty(
        name="Overwrite existing animation",
        description="Overwrite existing camera animation (if any)",
        default=False,
        options={'SKIP_SAVE'}
    )

    # ==============================================================================================
    # number of tracks (used only for `aerial_grid`)
    number_tracks: bpy.props.IntProperty(
        name="Number of parallel tracks",
        description="Number of parallel tracks",
        min=1,
        soft_max=100,
        default=6,
        options={'SKIP_SAVE'}
    )

    # ==============================================================================================
    # number of images in each track (used only for `aerial_grid`)
    number_images_per_track: bpy.props.IntProperty(
        name="Number of images per track",
        description="Number of images in each parallel track",
        min=1,
        soft_max=100,
        default=10,
        options={'SKIP_SAVE'}
    )

    # ==============================================================================================
    # animation side direction (used only for `aerial_grid`)
    side_direction: bpy.props.EnumProperty(
        name="Side direction",
        description="Side animation direction",
        items=[
            ("animdirection.right", "Right", "Right"),
            ("animdirection.left", "Left", "Left"),
        ],
        default="animdirection.right",
        options={'SKIP_SAVE'}
    )

    # ==============================================================================================
    # image overlap along-track (used only for `aerial_grid`)
    overlap_along_track_percentage: bpy.props.IntProperty(
        name="Image overlap along-track",
        description="Percentage of image overlap for adjacent images along the same track",
        min=0,
        max=100,
        soft_max=99,
        default=80,
        subtype='PERCENTAGE',
        options={'SKIP_SAVE'}
    )

    # ==============================================================================================
    # image overlap across-tracks (used only for `aerial_grid`)
    overlap_across_track_percentage: bpy.props.IntProperty(
        name="Image overlap across-track",
        description="Percentage of image overlap for the images across adjacent tracks",
        min=0,
        max=100,
        soft_max=99,
        default=60,
        subtype='PERCENTAGE',
        options={'SKIP_SAVE'}
    )

    ################################################################################################
    # Layout
    #

    def draw(self, context: bpy.types.Context):
        """Operator layout"""
        layout = self.layout
        if context.active_object.animation_data is not None:   # camera has animation data
            layout.prop(self, "overwrite_existing_animation")
        row = layout.split(factor=0.33, align=True)
        row.label(text="Animation type")
        row.prop(self, "animation_type", text="")
        #
        if self.animation_type in ("animtype.helix", "animtype.circular_up"):
            row = layout.split(factor=0.33, align=True)
            row.separator_spacer()
            row = row.row(align=True)
            row.prop(self, "animation_height", text="Height")
            row.prop(self, "animation_turns", text="Turns")
        #
        if self.animation_type == "animtype.aerial_grid":
            layout.prop(self, "number_tracks")
            layout.prop(self, "number_images_per_track")
            row = layout.row(align=True)
            row.label(text="Side direction")
            row.prop(self, "side_direction", expand=True)
            row = layout.row(align=True)
            row.prop(self, "overlap_along_track_percentage", text="Along-track overlap")
            row.prop(self, "overlap_across_track_percentage", text="Across-track overlap")
            row = layout.row()
            row.enabled = False
            row.prop(context.scene.sfmflow, "scene_ground_average_z")
            #
            return    # TODO use randomized position on aerial grid?
        layout.prop(self, "images_count")
        layout.prop(self, "randomize_camera_pose")

    ################################################################################################
    # Behavior
    #

    # ==============================================================================================
    @classmethod
    def poll(cls, context: bpy.types.Context) -> bool:
        """Operator's enabling condition.
        The operator is enabled only if a render camera is selected and active.

        Arguments:
            context {bpy.types.Context} -- poll context

        Returns:
            bool -- True to enable, False to disable
        """
        return is_active_object_camera(context)

    # ==============================================================================================
    def invoke(self, context: bpy.types.Context, event: bpy.types.Event) -> set:  # pylint: disable=unused-argument
        """Init operator when invoked.

        Arguments:
            context {bpy.types.Context} -- invoke context
            event {bpy.types.Event} -- invoke event

        Returns:
            set -- enum set in {‘RUNNING_MODAL’, ‘CANCELLED’, ‘FINISHED’, ‘PASS_THROUGH’, ‘INTERFACE’}
        """
        self._scene_bbox = SceneBoundingBox(context.scene)
        self.animation_height = self._scene_bbox.height
        self.animation_turns = int(self.animation_height // 0.5)  # make approx one turn each 0.5 height
        #
        wm = context.window_manager
        return wm.invoke_props_dialog(self)

    # ==============================================================================================
    def execute(self, context: bpy.types.Context) -> set:
        """Animate the camera based on user's settings.

        Returns:
            set -- {'FINISHED'}
        """
        logger.info("Animating camera...")

        if not is_active_object_camera(context):
            msg = "No render camera selected!"
            logger.error(msg)
            self.report({'ERROR'}, msg)
            return {'CANCELLED'}
        #
        scene = context.scene
        camera = context.active_object
        bbox = self._scene_bbox
        #
        # define animation start frame
        displayed_frame = scene.frame_current                  # frame to be restored at end
        if self.overwrite_existing_animation:
            bpy.ops.sfmflow.animate_camera_clear('EXEC_DEFAULT')  # clear existing animation
            start_frame = scene.frame_start
        else:
            lk = get_last_keyframe(camera)
            start_frame = lk + 1 if lk else scene.frame_start  # animation start frame
        current_frame = start_frame
        #
        # ------------------------------------------------------------------------------------------
        if self.animation_type == "animtype.helix":
            # define camera target
            target = bbox.center.copy()
            target.z = camera.location.z   # to get distance at the same height (2D distance)
            target_empty = set_camera_target(camera, bbox.center, camera.name + " Target")
            # define helix params and sample positions on it
            points_per_turn = int(self.images_count // self.animation_turns)
            points = sample_points_on_helix(start_center=target, start_point=camera.location,
                                            turns=self.animation_turns, points_per_turn=points_per_turn,
                                            height=self.animation_height, randomize=self.randomize_camera_pose)
            if self.images_count != len(points):
                # FIXME is not guaranteed that the total images is exactly the requested
                msg = "Requested {} frames but sampled only {}!".format(self.images_count, len(points))
                logger.warning(msg)
                self.report({'WARNING'}, msg)
            # set keyframes
            last_z = points[0].z
            for p in points:
                camera.location = p
                camera.keyframe_insert(data_path="location", frame=current_frame)
                target_empty.location.z = (p.z - last_z)
                target_empty.keyframe_insert(data_path="location", frame=current_frame)
                set_camera_focus_to_intersection(context.view_layer, camera, scene, current_frame)
                current_frame += 1
        #
        # ------------------------------------------------------------------------------------------
        elif self.animation_type == "animtype.hemisphere":
            set_camera_target(camera, bbox.center, camera.name + " Target")
            r = euclidean_distance(bbox.center, camera.location)   # get radius from current camera position
            points = sample_points_on_hemisphere(center=bbox.center, radius=r, samples=self.images_count,
                                                 randomize=self.randomize_camera_pose)
            # set keyframes
            for p in points:
                camera.location = p
                camera.keyframe_insert(data_path="location", frame=current_frame)
                set_camera_focus_to_intersection(context.view_layer, camera, scene, current_frame)
                current_frame += 1
        #
        # ------------------------------------------------------------------------------------------
        elif self.animation_type == "animtype.circular":
            # define camera target
            target = bbox.center.copy()
            target.z = camera.location.z   # to get distance at the same height (2D distance)
            target_empty = set_camera_target(camera, bbox.center, camera.name + " Target")
            # sample positions on circle
            points = sample_points_on_circle(center=target, start_point=camera.location, points_count=self.images_count,
                                             randomize=self.randomize_camera_pose)
            # set keyframes
            for p in points:
                camera.location = p
                camera.keyframe_insert(data_path="location", frame=current_frame)
                set_camera_focus_to_intersection(context.view_layer, camera, scene, current_frame)
                current_frame += 1
        #
        # ------------------------------------------------------------------------------------------
        elif self.animation_type == "animtype.circular_up":
            # define camera target
            target = bbox.center.copy()
            target.z = camera.location.z  # start from bottom
            target_empty = set_camera_target(camera, target, camera.name + " Target")
            # define circle params and sample points on it
            turn_increment = self.animation_height / (self.animation_turns - 1)
            points_per_turn = int(self.images_count // self.animation_turns)
            points = sample_points_on_circle(center=target, start_point=camera.location, points_count=points_per_turn,
                                             randomize=self.randomize_camera_pose)
            if self.images_count != (len(points)*self.animation_turns):
                # FIXME is not guaranteed that the total images is exactly the requested
                msg = "Requested {} frames but sampled only {}!".format(
                    self.images_count, (len(points)*self.animation_turns))
                logger.warning(msg)
                self.report({'WARNING'}, msg)
            # set keyframes
            target.z = bbox.z_min
            last_z = target_empty.location.z
            for t in range(self.animation_turns):
                target_empty.location.z = target.z + t * turn_increment
                target_empty.keyframe_insert(data_path="location", frame=current_frame)
                for p in points:
                    camera.location = p
                    camera.keyframe_insert(data_path="location", frame=current_frame)
                    set_camera_focus_to_intersection(context.view_layer, camera, scene, current_frame)
                    current_frame += 1
                target_empty.keyframe_insert(data_path="location", frame=current_frame-1)
        #
        # ------------------------------------------------------------------------------------------
        elif self.animation_type == "animtype.aerial_grid":
            try:
                _, footprint = get_ground_sample_distance(camera, scene, scene.sfmflow.scene_ground_average_z)
            except (RuntimeError, NotImplementedError) as e:
                msg = str(e)
                logger.error(msg)
                self.report({'ERROR'}, msg)
                return {'CANCELLED'}
            step_forward = footprint[1] - footprint[1] * self.overlap_along_track_percentage / 100
            step_side = footprint[0] - footprint[0] * self.overlap_across_track_percentage / 100
            #
            sign_side = 1. if self.side_direction == "animdirection.right" else -1.  # right = +, left = -
            p = camera.location
            for _ in range(self.number_tracks):   # for each track
                camera_up = get_camera_up(camera)
                forward_direction = Vector((camera_up.x, camera_up.y, 0)).normalized()
                side_direction = sign_side * get_camera_right(camera)
                #
                for i in range(self.number_images_per_track):   # for each image of the track
                    camera.location = p
                    camera.keyframe_insert(data_path="location", frame=current_frame)
                    camera.keyframe_insert(data_path="rotation_euler", frame=current_frame)
                    set_camera_focus_to_intersection(context.view_layer, camera, scene,
                                                     current_frame)   # FIXME do we really want this on aerial images?
                    #
                    current_frame += 1
                    if i < self.number_images_per_track - 1:
                        p += step_forward * forward_direction    # step forward
                #
                p += step_side * side_direction                  # step aside
                camera.rotation_euler.z += sign_side * radians(180)
                context.view_layer.update()   # update matrix_world after rotation
                sign_side *= -1.
        #
        # ------------------------------------------------------------------------------------------
        else:
            msg = "Unknown camera animation type!"
            logger.error(msg)
            self.report({'ERROR'}, msg)
            return {'CANCELLED'}
        #
        # set sequence frames
        if scene.frame_start > start_frame:
            scene.frame_start = start_frame
        if scene.frame_end < current_frame - 1:
            scene.frame_end = current_frame - 1
        scene.frame_step = 1
        scene.frame_current = displayed_frame
        #
        context.view_layer.update()
        #
        logger.info("Camera '%s' animated using animation type: %s.", camera.name, self.animation_type)
        return {'FINISHED'}


#
#
#
#


class SFMFLOW_OT_animate_camera_clear(bpy.types.Operator):
    """Clear the animation of the render camera"""
    bl_idname = "sfmflow.animate_camera_clear"
    bl_label = "Clear render camera animation"
    bl_options = {'REGISTER', 'UNDO'}

    ################################################################################################
    # Behavior
    #

    # ==============================================================================================
    @classmethod
    def poll(cls, context: bpy.types.Context) -> bool:
        """Panel's enabling condition.
        The operator is enabled only if the render camera has an animation path.

        Arguments:
            context {bpy.types.Context} -- poll context

        Returns:
            bool -- True to enable, False to disable
        """
        return is_active_object_camera(context) and context.active_object.animation_data is not None

    # ==============================================================================================
    def execute(self, context: bpy.types.Context) -> set:
        """Clear the render camera animation.

        Returns:
            set -- {'FINISHED'}
        """
        if not is_active_object_camera(context):
            msg = "No render camera selected!"
            logger.error(msg)
            self.report({'ERROR'}, msg)
            return {'CANCELLED'}
        #
        camera = context.active_object
        camera.animation_data_clear()
        #
        # remove track-to constraint
        track_to, constraint = get_track_to_constraint_target(camera)
        if track_to:
            camera.constraints.remove(constraint)
            bpy.data.objects.remove(track_to, do_unlink=True)
        # remove focus constraint
        if camera.data.dof.focus_object is not None:
            bpy.data.objects.remove(camera.data.dof.focus_object, do_unlink=True)
            camera.data.dof.focus_object = None
        #
        logger.info("Cleared animation for camera '%s'.", camera.name)
        return {'FINISHED'}

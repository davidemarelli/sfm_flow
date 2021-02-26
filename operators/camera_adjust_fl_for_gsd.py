
import logging
from math import pi

import bpy
from mathutils import Vector

from ..utils.camera import (get_camera_lookat, get_focal_length_for_gsd, get_ground_sample_distance,
                            is_active_object_camera)

logger = logging.getLogger(__name__)


class SFMFLOW_OT_camera_adjust_fl_for_gsd(bpy.types.Operator):
    """Adjust camera focal length to obtain the desired Ground Sample Distance (and vice-versa)"""
    bl_idname = "sfmflow.camera_adjust_fl_gsd"
    bl_label = "Adjust camera's FL and GSD"
    bl_options = {'REGISTER', 'UNDO'}

    ################################################################################################
    # Properties
    #

    lock = False

    def _update_gsd(self, context):
        if not SFMFLOW_OT_camera_adjust_fl_for_gsd.lock:
            camera = context.active_object
            if camera.data.lens != self.focal_length * 1000:
                camera.data.lens = self.focal_length * 1000
            gsd, _ = get_ground_sample_distance(camera, context.scene,
                                                ground_level=context.scene.sfmflow.scene_ground_average_z)
            SFMFLOW_OT_camera_adjust_fl_for_gsd.lock = True
            self.gsd = gsd / 100  # convert to meters
            SFMFLOW_OT_camera_adjust_fl_for_gsd.lock = False

    def _update_fl(self, context):
        if not SFMFLOW_OT_camera_adjust_fl_for_gsd.lock:
            camera = context.active_object
            fl = get_focal_length_for_gsd(camera, context.scene, self.gsd * 100,
                                          ground_level=context.scene.sfmflow.scene_ground_average_z)
            fl = 1 if fl < 1 else fl   # minimum allowed focal length is 1 mm
            camera.data.lens = fl
            SFMFLOW_OT_camera_adjust_fl_for_gsd.lock = True
            self.focal_length = fl / 1000
            if fl == 1:   # 1 mm
                gsd, _ = get_ground_sample_distance(camera, context.scene,
                                                    ground_level=context.scene.sfmflow.scene_ground_average_z)
                self.gsd = gsd / 100  # convert to meters
            SFMFLOW_OT_camera_adjust_fl_for_gsd.lock = False

    # ==============================================================================================
    # focal length
    focal_length: bpy.props.FloatProperty(
        name="Focal length",
        description="Focal length",
        unit='LENGTH',
        precision=3,
        soft_min=0.001,
        min=0.001,
        soft_max=1.,
        update=_update_gsd,
        options={'SKIP_SAVE'}
    )

    # ==============================================================================================
    # gsd
    gsd: bpy.props.FloatProperty(
        name="GSD",
        description="Ground sample distance",
        unit='LENGTH',
        precision=3,
        soft_min=0.001,
        soft_max=10.,
        update=_update_fl,
        options={'SKIP_SAVE'}
    )

    ################################################################################################
    # Layout
    #

    def draw(self, context: bpy.types.Context):
        """Operator layout"""
        layout = self.layout
        row = layout.row()
        row.enabled = False
        row.prop(context.scene.sfmflow, "scene_ground_average_z")
        layout.prop(self, "focal_length")
        layout.prop(self, "gsd")

    ################################################################################################
    # Behavior
    #

    # ==============================================================================================
    @classmethod
    def poll(cls, context: bpy.types.Context) -> bool:
        """Operator's enabling condition.
        The operator is enabled only if a render camera is active and is looking towards teh ground.

        Arguments:
            context {bpy.types.Context} -- poll context

        Returns:
            bool -- True to enable, False to disable
        """
        if is_active_object_camera(context):
            camera = context.active_object
            alpha = Vector((0, 0, -1)).angle(get_camera_lookat(camera))
            if alpha < pi/2:   # the camera is looking to the ground, makes sense to compute the GSD
                return True
        return False

    # ==============================================================================================
    def invoke(self, context: bpy.types.Context, event: bpy.types.Event) -> set:  # pylint: disable=unused-argument
        """Init operator when invoked.

        Arguments:
            context {bpy.types.Context} -- invoke context
            event {bpy.types.Event} -- invoke event

        Returns:
            set -- enum set in {‘RUNNING_MODAL’, ‘CANCELLED’, ‘FINISHED’, ‘PASS_THROUGH’, ‘INTERFACE’}
        """
        self.backup_focal_length = context.active_object.data.lens   # pylint: disable=attribute-defined-outside-init
        #
        SFMFLOW_OT_camera_adjust_fl_for_gsd.lock = True
        gsd, _ = get_ground_sample_distance(context.active_object, context.scene)
        self.gsd = gsd / 100   # convert to meters
        self.focal_length = context.active_object.data.lens / 1000
        SFMFLOW_OT_camera_adjust_fl_for_gsd.lock = False
        #
        wm = context.window_manager
        return wm.invoke_props_dialog(self)

    # ==============================================================================================
    def execute(self, context: bpy.types.Context) -> set:   # pylint: disable=unused-argument
        """Confirm current camera setup (do nothing, focal length is updated by _update_gsd and _update_fl).

        Returns:
            set -- {'FINISHED'}
        """
        return {'FINISHED'}

    # ==============================================================================================
    def cancel(self, context: bpy.types.Context) -> None:
        """If operator is cancelled restore original camera's focal length."""
        if self.backup_focal_length:
            context.active_object.data.lens = self.backup_focal_length

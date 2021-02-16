
import logging
from math import pi

import bpy
from mathutils import Vector

from ..utils import get_cameras_collection

logger = logging.getLogger(__name__)


class SFMFLOW_OT_camera_add(bpy.types.Operator):
    """Add a camera or multiple cameras from available presets to the current scene."""
    bl_idname = "sfmflow.camera_add"
    bl_label = "Add camera"
    bl_options = {'REGISTER', 'UNDO'}

    ################################################################################################
    # Properties
    #

    # ==============================================================================================
    camera_type: bpy.props.EnumProperty(
        name="Camera type",
        description="Choose a camera type",
        items=[
            ("camtype.single", "Single", "Single camera with default parameters."),
            ("camtype.uav_1", "UAV - 1 camera", "UAV with a single nadir camera."),
            ("camtype.uav_5", "UAV - 5 cameras", "UAV with nadir and oblique cameras."),
        ],
        default="camtype.single",
        options={'SKIP_SAVE'}
    )

    # ==============================================================================================
    location: bpy.props.FloatVectorProperty(
        size=3,
        default=(0., 0., 0.),
        precision=1,
        subtype="XYZ",
        options={'SKIP_SAVE'}
    )

    ################################################################################################
    # Layout
    #

    def draw(self, context: bpy.types.Context):   # pylint: disable=unused-argument
        """Operator layout"""
        layout = self.layout
        row = layout.split(factor=0.33, align=True)
        row.label(text="Animation type")
        row.prop(self, "camera_type", text="")
        row = layout.split(factor=0.33, align=True)
        row.label(text="Location")
        row.prop(self, "location", text="")

    ################################################################################################
    # Behavior
    #

    # ==============================================================================================
    @classmethod
    def poll(cls, context: bpy.types.Context) -> bool:
        """Operator's enabling condition.
        The operator is enabled only if a scene is present.

        Arguments:
            context {bpy.types.Context} -- poll context

        Returns:
            bool -- True to enable, False to disable
        """
        return context.scene is not None

    # ==============================================================================================
    def invoke(self, context: bpy.types.Context, event: bpy.types.Event) -> set:  # pylint: disable=unused-argument
        """Init operator data when invoked.

        Arguments:
            context {bpy.types.Context} -- invoke context
            event {bpy.types.Event} -- invoke event

        Returns:
            set -- enum set in {‘RUNNING_MODAL’, ‘CANCELLED’, ‘FINISHED’, ‘PASS_THROUGH’, ‘INTERFACE’}
        """
        self.location = context.scene.cursor.location
        #
        wm = context.window_manager
        return wm.invoke_props_dialog(self)

    # ==============================================================================================
    def execute(self, context: bpy.types.Context) -> set:
        """Add a ground control point.

        Returns:
            set -- {'FINISHED'}
        """
        cameras_collection = get_cameras_collection()
        properties = context.scene.sfmflow
        new_cameras = []
        #
        # ------------------------------------------------------------------------------------------
        if self.camera_type == "camtype.single":
            camera = self._create_new_camera(location=self.location)
            cameras_collection.objects.link(camera)
            new_cameras.append(camera)
        #
        # ------------------------------------------------------------------------------------------
        elif self.camera_type == "camtype.uav_1":
            camera = self._create_new_camera(name="UAV nadir", location=self.location,
                                             rotation_euler=Vector((0., 0., 0.)))
            cameras_collection.objects.link(camera)
            new_cameras.append(camera)
        #
        # ------------------------------------------------------------------------------------------
        elif self.camera_type == "camtype.uav_5":
            camera_n = self._create_new_camera(name="UAV nadir", location=self.location,
                                               rotation_euler=Vector((0., 0., 0.)))
            camera_f = self._create_new_camera(name="UAV forward", location=self.location,
                                               rotation_euler=Vector((pi/4, 0., 0.)))
            camera_b = self._create_new_camera(name="UAV backward", location=self.location,
                                               rotation_euler=Vector((pi/4, 0., pi)))
            camera_l = self._create_new_camera(name="UAV left", location=self.location,
                                               rotation_euler=Vector((pi/4, 0., pi/2)))
            camera_r = self._create_new_camera(name="UAV right", location=self.location,
                                               rotation_euler=Vector((pi/4, 0., -pi/2)))
            #
            cameras_collection.objects.link(camera_n)
            cameras_collection.objects.link(camera_f)
            cameras_collection.objects.link(camera_b)
            cameras_collection.objects.link(camera_l)
            cameras_collection.objects.link(camera_r)
            #
            # set parent
            context.view_layer.update()
            parent_inv_mw = camera_n.matrix_world.inverted()
            camera_f.parent = camera_n
            camera_f.matrix_parent_inverse = parent_inv_mw
            camera_b.parent = camera_n
            camera_b.matrix_parent_inverse = parent_inv_mw
            camera_l.parent = camera_n
            camera_l.matrix_parent_inverse = parent_inv_mw
            camera_r.parent = camera_n
            camera_r.matrix_parent_inverse = parent_inv_mw
            #
            new_cameras.append(camera_n)
            new_cameras.append(camera_f)
            new_cameras.append(camera_b)
            new_cameras.append(camera_l)
            new_cameras.append(camera_r)
        #
        # ------------------------------------------------------------------------------------------
        else:
            msg = "Unknown camera type ({})!".format(self.camera_type)
            logger.error(msg)
            self.report({'ERROR'}, msg)
            return {'CANCELLED'}
        #
        # add new cameras to the render cameras
        idx_backup = properties.render_cameras_idx
        for c in new_cameras:
            if 0 <= properties.render_cameras_idx < len(properties.render_cameras):
                properties.render_cameras[properties.render_cameras_idx].camera = c
                properties.render_cameras_idx = -1
            else:
                c_prop = properties.render_cameras.add()
                c_prop.camera = c
        properties.render_cameras_idx = idx_backup
        #
        context.view_layer.update()   # update matrix_world after rotation
        return {'FINISHED'}

    ################################################################################################
    # Methods
    #

    # ==============================================================================================
    def _create_new_camera(self, name: str = "Camera", location: Vector = Vector((0., 0., 0.)),
                           rotation_euler: Vector = Vector((1.11, 0., 0.82))) -> bpy.types.Camera:
        #
        # --- create camera data
        cam_data = bpy.data.cameras.new(name)
        # lens
        cam_data.type = 'PERSP'
        cam_data.lens = 35.0                  # focal length in millimeters
        cam_data.lens_unit = 'MILLIMETERS'
        cam_data.shift_x = 0.000
        cam_data.shift_y = 0.000
        cam_data.clip_start = 0.100
        cam_data.clip_end = 1000.0
        # sensor
        cam_data.sensor_width = 32            # sensor width in millimeters
        cam_data.sensor_height = 18           # sensor height in millimeters
        cam_data.sensor_fit = 'HORIZONTAL'
        # depth of field
        cam_data.dof.aperture_fstop = 2.8
        cam_data.dof.aperture_blades = 0
        cam_data.dof.aperture_rotation = 0.0
        cam_data.dof.aperture_ratio = 1.0
        # viewport display
        cam_data.show_limits = True
        cam_data.display_size = 0.50
        #
        # --- create camera object
        camera = bpy.data.objects.new(name, cam_data)
        camera.location = location
        camera.rotation_euler = rotation_euler
        #
        return camera

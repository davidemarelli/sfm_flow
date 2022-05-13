
import logging
from math import pi
from typing import List, Tuple

import bpy
from mathutils import Vector
from sfm_flow.utils import get_cameras_collection

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
    # camera offset for multi-cameras setup, specify the ±X and ±Y offset from the main camera
    cameras_offset: bpy.props.FloatVectorProperty(
        name="Camera offset from the main camera",
        size=2,
        default=(0.2, 0.2),
        precision=4,
        min=0.,
        soft_max=1.,
        subtype='TRANSLATION',
        options={'SKIP_SAVE'}
    )

    # ==============================================================================================
    camera_preset: bpy.props.EnumProperty(
        name="Camera preset",
        description="Choose a camera type",
        items=[
            ("campreset.default", "Default preset", "Default SFM Flow camera parameters."),
            ("campreset.nikon_D750", "Nikon D750", "Nikon D750 camera parameters."),
            ("campreset.sony_a7III", "Sony a7 III", "Sony a7 III camera parameters."),
        ],
        default="campreset.default",
        options={'SKIP_SAVE'}
    )

    CAMERA_PRESETS = {
        "campreset.default": {
            "maker": "Blender",
            "model": "SfM Flow",
            "resolutions": [(1920, 1080)],
            "sensor_size": (36, 24),
        },
        "campreset.nikon_D750": {
            "maker": "NIKON CORPORATION",
            "model": "NIKON D750",
            "resolutions": [(6016, 4016), (4512, 3008), (3008, 2008), (5008, 3336), (3752, 2504),
                            (3936, 2624), (2944, 1968), (1968, 1312)],
            "sensor_size": (35.9, 24),
            "px_size": 0.00595,   # px size on the sensor in mm
        },
        "campreset.sony_a7III": {
            "maker": "SONY",
            "model": "ILCE-7M3",   # cspell:ignore ILCE
            "resolutions": [(6000, 4000), (6000, 3376), (3936, 2624), (3936, 2216), (3008, 1688), (3008, 2000)],
            "sensor_size": (35.8, 23.8),
            "px_size": 0.00591,   # px size on the sensor in mm
        }
    }

    # ==============================================================================================
    def _get_render_resolution_items(self, context: bpy.types.Context) -> List[Tuple[str, str, str, int]]:   # pylint: disable=unused-argument
        """Get the list of available resolutions of the current camera preset.

        Arguments:
            context {bpy.context} -- current context

        Returns:
            List[Tuple[str, str, str, int]] -- List of {EnumProperty} items
        """
        items = []
        if self.camera_preset in SFMFLOW_OT_camera_add.CAMERA_PRESETS:
            for i, res in enumerate(SFMFLOW_OT_camera_add.CAMERA_PRESETS[self.camera_preset]['resolutions']):
                res_name = f"{res[0]}x{res[1]}"
                items.append(("imgres." + res_name, res_name, "", i))
        items.append(("imgres.custom", "Custom resolution", "", len(items)))
        return items

    set_image_resolution: bpy.props.BoolProperty(
        name="Set image resolution",
        description="Set image resolution",
        default=True,
        options={'SKIP_SAVE'}
    )

    image_resolution: bpy.props.EnumProperty(
        name="Image resolution",
        description="Image resolution",
        items=_get_render_resolution_items,
        options={'SKIP_SAVE'}
    )

    # ==============================================================================================
    custom_image_resolution_x: bpy.props.IntProperty(
        name="Image resolution X",
        description="Image resolution X",
        min=1,
        soft_max=15360,
        subtype='PIXEL',
        options={'SKIP_SAVE'}
    )

    custom_image_resolution_y: bpy.props.IntProperty(
        name="Image resolution Y",
        description="Image resolution Y",
        min=1,
        soft_max=8640,
        subtype='PIXEL',
        options={'SKIP_SAVE'}
    )

    # ==============================================================================================
    location: bpy.props.FloatVectorProperty(
        name="Insert location for the new camera/s",
        size=3,
        default=(0., 0., 0.),
        precision=4,
        subtype='TRANSLATION',
        options={'SKIP_SAVE'}
    )

    ################################################################################################
    # Layout
    #

    def draw(self, context: bpy.types.Context):   # pylint: disable=unused-argument
        """Operator layout"""
        layout = self.layout
        row = layout.split(factor=0.25, align=True)
        row.label(text="Type")
        row.prop(self, "camera_type", text="")
        if self.camera_type == "camtype.uav_5":
            row = layout.split(factor=0.25, align=True)
            row.label(text="Offset")
            row.row().prop(self, "cameras_offset", text="")
        row = layout.split(factor=0.25, align=True)
        row.label(text="Preset")
        row.prop(self, "camera_preset", text="")
        row = layout.split(factor=0.5, align=True)
        row.prop(self, "set_image_resolution")
        if self.set_image_resolution:
            row.prop(self, "image_resolution", text="")
            if self.image_resolution == "imgres.custom":
                row = layout.split(factor=0.25, align=True)
                row.separator_spacer()
                row = row.row(align=True)
                row.prop(self, "custom_image_resolution_x", text="")
                row.label(text="", icon='X')
                row.prop(self, "custom_image_resolution_y", text="")
        row = layout.split(factor=0.25, align=True)
        row.label(text="Location")
        row.row().prop(self, "location", text="")

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
        self.custom_image_resolution_x = context.scene.render.resolution_x
        self.custom_image_resolution_y = context.scene.render.resolution_y
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
        sensor_size = SFMFLOW_OT_camera_add.CAMERA_PRESETS[self.camera_preset]['sensor_size']
        px_size = SFMFLOW_OT_camera_add.CAMERA_PRESETS[self.camera_preset]['px_size']
        maker = SFMFLOW_OT_camera_add.CAMERA_PRESETS[self.camera_preset]['maker']
        model = SFMFLOW_OT_camera_add.CAMERA_PRESETS[self.camera_preset]['model']
        #
        # ------------------------------------------------------------------------------------------
        if self.camera_type == "camtype.single":
            camera = self._create_new_camera(location=self.location, sensor_size=sensor_size)
            camera.data['sfmflow.maker'] = maker
            camera.data['sfmflow.model'] = model
            camera.data['sfmflow.px_size'] = px_size
            cameras_collection.objects.link(camera)
            new_cameras.append(camera)
        #
        # ------------------------------------------------------------------------------------------
        elif self.camera_type == "camtype.uav_1":
            camera = self._create_new_camera(name="UAV nadir", location=self.location,
                                             rotation_euler=Vector((0., 0., 0.)), sensor_size=sensor_size)
            camera.data['sfmflow.maker'] = maker
            camera.data['sfmflow.model'] = model
            camera.data['sfmflow.px_size'] = px_size
            cameras_collection.objects.link(camera)
            new_cameras.append(camera)
        #
        # ------------------------------------------------------------------------------------------
        elif self.camera_type == "camtype.uav_5":
            offset = self.cameras_offset
            camera_n = self._create_new_camera(name="UAV nadir", location=self.location,
                                               rotation_euler=Vector((0., 0., 0.)), sensor_size=sensor_size)
            camera_f = self._create_new_camera(name="UAV forward", location=self.location + Vector((0, offset[1], 0)),
                                               rotation_euler=Vector((pi/4, 0., 0.)), sensor_size=sensor_size)
            camera_b = self._create_new_camera(name="UAV backward", location=self.location - Vector((0, offset[1], 0)),
                                               rotation_euler=Vector((pi/4, 0., pi)), sensor_size=sensor_size)
            camera_l = self._create_new_camera(name="UAV left", location=self.location - Vector((offset[0], 0, 0)),
                                               rotation_euler=Vector((pi/4, 0., pi/2)), sensor_size=sensor_size)
            camera_r = self._create_new_camera(name="UAV right", location=self.location + Vector((offset[0], 0, 0)),
                                               rotation_euler=Vector((pi/4, 0., -pi/2)), sensor_size=sensor_size)
            #
            camera_n.data['sfmflow.maker'] = maker
            camera_n.data['sfmflow.model'] = model
            camera_n.data['sfmflow.px_size'] = px_size
            camera_f.data['sfmflow.maker'] = maker
            camera_f.data['sfmflow.model'] = model
            camera_f.data['sfmflow.px_size'] = px_size
            camera_b.data['sfmflow.maker'] = maker
            camera_b.data['sfmflow.model'] = model
            camera_b.data['sfmflow.px_size'] = px_size
            camera_l.data['sfmflow.maker'] = maker
            camera_l.data['sfmflow.model'] = model
            camera_l.data['sfmflow.px_size'] = px_size
            camera_r.data['sfmflow.maker'] = maker
            camera_r.data['sfmflow.model'] = model
            camera_r.data['sfmflow.px_size'] = px_size
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
            msg = f"Unknown camera type ({self.camera_type})!"
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
        # set render image resolution
        if self.set_image_resolution:
            if self.image_resolution == "imgres.custom":
                context.scene.render.resolution_x = self.custom_image_resolution_x
                context.scene.render.resolution_y = self.custom_image_resolution_y
            else:
                # TODO get tuple from CAMERA_PRESETS
                res = tuple(map(int, self.image_resolution.replace("imgres.", '').split('x')))
                context.scene.render.resolution_x = res[0]
                context.scene.render.resolution_y = res[1]
                #
        context.view_layer.update()   # update matrix_world after rotation
        return {'FINISHED'}

    ################################################################################################
    # Methods
    #

    # ==============================================================================================
    def _create_new_camera(self, name: str = "Camera", location: Vector = Vector((0., 0., 0.)),
                           rotation_euler: Vector = Vector((1.11, 0., 0.82)),
                           sensor_size: Tuple[float, float] = (36., 24.)) -> bpy.types.Camera:
        """Create a new camera object and its data block. The camera object will not be linked to the scene.

        Keyword Arguments:
            name {str} -- name of the new camera (default: {"Camera"})
            location {Vector} -- 3D location of the new camera (default: {Vector((0., 0., 0.))})
            rotation_euler {Vector} -- rotation of the new camera in radians (default: {Vector((1.11, 0., 0.82))})
            sensor_size {Tuple[float, float]} -- sensor size of the new camera (default: {(36., 24.)})

        Returns:
            bpy.types.Camera --
        """
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
        cam_data.sensor_width = sensor_size[0]    # sensor width in millimeters
        cam_data.sensor_height = sensor_size[1]   # sensor height in millimeters
        cam_data.sensor_fit = 'HORIZONTAL' if sensor_size[0] > sensor_size[1] else 'VERTICAL'
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

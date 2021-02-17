
import logging
from collections import namedtuple
from math import pi
from random import random

import addon_utils
import bpy
from mathutils import Euler, Vector

from ..prefs import SFMFLOW_AddonProperties
from ..utils import (BlenderVersion, SceneBoundingBox, camera_detect_dof_distance,
                     euclidean_distance, get_environment_collection)
from ..utils.nodes import add_floor_material_nodes

logger = logging.getLogger(__name__)


class SFMFLOW_OT_init_scene(bpy.types.Operator):
    """Initializes the current scene for SfM dataset generation"""
    bl_idname = "sfmflow.init_scene"
    bl_label = "Initialize current scene"
    bl_options = {'REGISTER', 'UNDO'}

    # scene bounding box, set on invoke and used in multiple init methods
    scene_bbox = None   # type: SceneBoundingBox

    # default sun orientation
    DEFAULT_SUN_ROTATION = Euler((0.9599310755729675, 0.0, 0.2617993950843811), 'XYZ')

    ################################################################################################
    # Properties
    #

    # ==============================================================================================
    scene_type: bpy.props.EnumProperty(
        name="Scene type",
        description="Scene initialization type",
        items=[
            ("scenetype.floor", "Floor", "Add a ground floor under the scene"),
            ("scenetype.sphere", "Hemisphere", "Include the scene in a smooth hemisphere"),
            ("scenetype.none", "None", "No additional scene elements"),
        ],
        default="scenetype.floor",
        options={'SKIP_SAVE'}
    )

    # ==============================================================================================
    sphere_radius: bpy.props.FloatProperty(
        name="Radius",
        description="Radius for wall-sphere that incorporates the scene",
        min=0.0,
        soft_min=1.,
        subtype='DISTANCE'
    )

    # ==============================================================================================
    lights_type: bpy.props.EnumProperty(
        name="Lighting type",
        description="Scene illumination setup type",
        items=[
            ("lightstype.sun", "Sky & sun", "Add a sky and sun to the scene"),
            ("lightstype.point", "Point lights", "Add some default point lights to the scene"),
            ("lightstype.none", "None", "No lights"),
        ],
        default="lightstype.sun",
        options={'SKIP_SAVE'}
    )

    # ==============================================================================================
    is_init_camera: bpy.props.BoolProperty(
        name="Initialize default render camera",
        description="Initialize the scene's default render camera",
        default=False,
        options={'SKIP_SAVE'}
    )

    ################################################################################################
    # Layout
    #

    def draw(self, context: bpy.types.Context):   # pylint: disable=unused-argument
        """Operator panel layout"""
        layout = self.layout
        row = layout.split(factor=0.33, align=True)
        row.alignment = 'RIGHT'
        row.label(text="Scene type")
        row.prop(self, "scene_type", text="")
        if self.scene_type == "scenetype.sphere":
            row = layout.split(factor=0.33, align=True)
            row.alignment = 'RIGHT'
            row.separator_spacer()
            row.prop(self, "sphere_radius")
        row = layout.split(factor=0.33, align=True)
        row.alignment = 'RIGHT'
        row.label(text="Lighting type")
        row.prop(self, "lights_type", text="")
        row = layout.row(align=True)
        row.alignment = 'RIGHT'
        #
        camera = context.scene.camera
        if camera and camera not in context.scene.sfmflow.get_render_cameras():
            # show camera init if current scene.camera is not an sfmflow's render camera
            self.is_init_camera = True
            row.label(text="Initialize default render camera")
            row.prop(self, "is_init_camera", icon_only=True)

    ################################################################################################
    # Behavior
    #

    # ==============================================================================================
    @classmethod
    def poll(cls, context: bpy.types.Context) -> bool:
        """Panel's enabling condition.
        The operator is enabled only if the scene is not yet initialized.

        Arguments:
            context {bpy.types.Context} -- poll context

        Returns:
            bool -- True to enable, False to disable
        """
        return not context.scene.sfmflow.is_scene_init

    # ==============================================================================================
    def invoke(self, context: bpy.types.Context, event: bpy.types.Event) -> set:  # pylint: disable=unused-argument
        """Init operator when invoked.

        Arguments:
            context {bpy.types.Context} -- invoke context
            event {bpy.types.Event} -- invoke event

        Returns:
            set -- enum set in {‘RUNNING_MODAL’, ‘CANCELLED’, ‘FINISHED’, ‘PASS_THROUGH’, ‘INTERFACE’}
        """
        # check cycles availability
        if addon_utils.check("cycles")[1] is False:
            msg = "Cycles is required but not enabled on your install. Please enable it in Preferences."
            self.report({'ERROR'}, msg)
            logger.error(msg)
            return {'CANCELLED'}
        #
        # compute a default sphere-wall radius
        self.scene_bbox = SceneBoundingBox(context.scene)  # type: SceneBoundingBox
        dist1 = euclidean_distance(self.scene_bbox.center, self.scene_bbox.get_min_vector())
        dist2 = euclidean_distance(self.scene_bbox.center, self.scene_bbox.get_max_vector())
        self.sphere_radius = max(dist1, dist2) * 20.
        #
        wm = context.window_manager
        return wm.invoke_props_dialog(self)

    # ==============================================================================================
    def execute(self, context: bpy.types.Context) -> set:
        """Initialize current scene.

        Arguments:
            context {bpy.types.Context} -- current context

        Returns:
            set -- {'FINISHED'}
        """
        scene = context.scene
        properties = context.scene.sfmflow
        camera = scene.camera
        if self.is_init_camera and (not camera):
            msg = "This scene has no render camera!"
            logger.error(msg)
            self.report({'ERROR'}, msg)
            return {'CANCELLED'}
        #
        SFMFLOW_OT_init_scene.init_scene(scene)
        if self.is_init_camera:
            SFMFLOW_OT_init_scene.init_camera(scene, camera, context.view_layer)
            # add the default camera to the render camera list
            render_camera = properties.render_cameras.add()
            render_camera.camera = camera
        #
        if self.scene_type == "scenetype.floor":
            self.add_floor(scene)
        elif self.scene_type == "scenetype.sphere":
            self.add_walls(scene, self.sphere_radius)
        elif self.scene_type != "scenetype.none":
            msg = "Unknown scene type!"
            logger.error(msg)
            self.report({'ERROR'}, msg)
            return {'CANCELLED'}
        #
        if self.lights_type == "lightstype.sun":
            SFMFLOW_OT_init_scene.setup_sky(context)
        elif self.lights_type == "lightstype.point":
            self.add_point_lights(scene)
        elif self.lights_type != "lightstype.none":
            msg = "Unknown lighting type!"
            logger.error(msg)
            self.report({'ERROR'}, msg)
            return {'CANCELLED'}
        #
        SFMFLOW_OT_init_scene.init_effects(scene, properties)
        #
        # everything ok, set flag to prevent re-init (operation is still undoable)
        context.scene.sfmflow.is_scene_init = True
        return {'FINISHED'}

    ################################################################################################
    # Helper methods
    #

    # ==============================================================================================
    @staticmethod
    def init_scene(scene: bpy.types.Scene) -> None:
        """Initialize the given scene with default values.

        Arguments:
            scene {scene} -- current scene
        """
        logger.info("Initializing scene: %s", scene.name)

        scene.render.engine = 'CYCLES'                   # switch to path tracing render engine
        scene.unit_settings.system = 'METRIC'            # switch to metric units

    # --- Render option
        if bpy.context.preferences.addons['cycles'].preferences.compute_device_type is not None:
            # CUDA or OpenCL
            scene.cycles.device = 'GPU'
        else:
            # CPU only
            scene.cycles.device = 'CPU'
        # images size and aspect ratio
        scene.render.pixel_aspect_x = 1.0
        scene.render.pixel_aspect_y = 1.0
        scene.render.resolution_x = 1920                 # width
        scene.render.resolution_y = 1080                 # height
        scene.render.resolution_percentage = 100         # rendering scale
        scene.render.use_border = False
        scene.render.use_crop_to_border = False
        # images metadata
        scene.render.use_stamp_time = True
        scene.render.use_stamp_date = True
        scene.render.use_stamp_render_time = True
        scene.render.use_stamp_frame = True
        scene.render.use_stamp_scene = True
        scene.render.use_stamp_memory = True
        scene.render.use_stamp_camera = True
        scene.render.use_stamp_lens = True
        scene.render.use_stamp_filename = True
        # image format
        scene.render.image_settings.color_mode = 'RGB'
        scene.sfmflow.render_file_format = 'JPEG'   # scene.render.image_settings.file_format is updated automatically
        scene.render.use_file_extension = True
        scene.render.use_overwrite = True                # force overwrite, be careful!
        scene.render.image_settings.quality = 90         # image compression
        # post processing
        scene.render.use_compositing = True
        scene.render.use_sequencer = False
        # sampling
        scene.cycles.progressive = 'BRANCHED_PATH'
        scene.cycles.seed = 0
        scene.cycles.sample_clamp_direct = 0
        scene.cycles.sample_clamp_indirect = 0
        scene.cycles.light_sampling_threshold = 0.01
        scene.cycles.aa_samples = 32
        scene.cycles.preview_aa_samples = 4
        scene.cycles.sample_all_lights_direct = True
        scene.cycles.sample_all_lights_indirect = True
        scene.cycles.diffuse_samples = 3
        scene.cycles.glossy_samples = 2
        scene.cycles.transmission_samples = 2
        scene.cycles.ao_samples = 1
        scene.cycles.mesh_light_samples = 2
        scene.cycles.subsurface_samples = 2
        scene.cycles.volume_samples = 2
        scene.cycles.sampling_pattern = 'SOBOL'
        scene.cycles.use_layer_samples = 'USE'
        # light paths
        scene.cycles.transparent_max_bounces = 8
        scene.cycles.transparent_min_bounces = 8
        scene.cycles.use_transparent_shadows = True
        scene.cycles.max_bounces = 8
        scene.cycles.min_bounces = 3
        scene.cycles.diffuse_bounces = 2
        scene.cycles.glossy_bounces = 4
        scene.cycles.transmission_bounces = 8
        scene.cycles.volume_bounces = 2
        scene.cycles.caustics_reflective = False
        scene.cycles.caustics_refractive = False
        scene.cycles.blur_glossy = 0.00
        # performances
        scene.render.threads_mode = 'AUTO'
        scene.cycles.debug_bvh_type = 'DYNAMIC_BVH'
        scene.cycles.preview_start_resolution = 64
        scene.cycles.tile_order = 'HILBERT_SPIRAL'
        scene.render.tile_x = 64
        scene.render.tile_y = 64
        scene.cycles.use_progressive_refine = False
        scene.render.use_save_buffers = False
        scene.render.use_persistent_data = False
        scene.cycles.debug_use_spatial_splits = False
        scene.cycles.debug_use_hair_bvh = True
        scene.cycles.debug_bvh_time_steps = 0

    # -- Color Management
        scene.view_settings.view_transform = "Standard"

    # -- Animation options
        scene.frame_start = 1
        scene.frame_end = 1
        scene.frame_step = 1
        scene.frame_current = 1

    # -- World options
        world = scene.world
        if world is None:
            world = bpy.data.worlds.new("World")
            world.use_sky_paper = True
            scene.world = world
        # noise reduction
        world.cycles.sample_as_light = True
        world.cycles.sample_map_resolution = 2048
        world.cycles.samples = 1
        world.cycles.max_bounces = 1024
        world.cycles.volume_sampling = 'EQUIANGULAR'
        world.cycles.volume_interpolation = 'LINEAR'
        world.cycles.homogeneous_volume = False

        logger.info("Scene initialized")

    # ==============================================================================================
    def add_walls(self, scene: bpy.types.Scene, walls_radius: float) -> None:
        """Add spherical wall to scene.

        Arguments:
            scene {scene} -- current scene
        """
        logger.info("Adding walls to scene: %s", scene.name)
        bbox = self.scene_bbox
        environment_collection = get_environment_collection()
        #
        # create scene walls
        bpy.ops.mesh.primitive_uv_sphere_add(location=bbox.center, radius=walls_radius)
        sphere = bpy.context.active_object
        sphere.name = "Walls"
        environment_collection.objects.link(sphere)
        bpy.context.collection.objects.unlink(sphere)   # sphere is created in the active collection, unlink and relink
        #
        # give the sphere a flat "floor"
        offset = 0.0001
        for vertex in sphere.data.vertices:
            v_world = sphere.matrix_world @ vertex.co   # sphere vertices are in obj space, move to world space
            if v_world.z < bbox.z_min:            # set Z=min(Z) to every vertex with Z<min(Z)
                v_world.z = bbox.z_min - offset   # tolerance to avoid z-fighting
            vertex.co = sphere.matrix_world.inverted() @ v_world  # move back to obj space
        sphere.data.flip_normals()
        #
        # setup wall material
        material = bpy.data.materials.new("Wall")
        material.use_nodes = True
        diffuse = material.node_tree.nodes.get("Principled BSDF")
        diffuse.inputs['Base Color'].default_value = (1.0, 1.0, 1.0, 1.0)
        diffuse.inputs['Roughness'].default_value = 0.0
        diffuse.inputs['Specular'].default_value = 0.0
        sphere.active_material = material
        #
        # add subdivision surface
        sphere.modifiers.new(name="SfM_WallSubSurf", type='SUBSURF')
        bpy.ops.object.shade_smooth()
        #
        logger.info("Walls added")

    # ==============================================================================================
    def add_point_lights(self, scene: bpy.types.Scene) -> None:
        """Add point lights to scene.

        Arguments:
            scene {scene} -- blender scene
        """
        logger.info("Adding lights to scene: %s", scene.name)
        bbox = self.scene_bbox
        environment_collection = get_environment_collection()
        #
        Light = namedtuple("light", "name location type colorRGBA strength")
        lights = (
            Light("Lamp DX - Front", (bbox.center.x + 5.0, bbox.center.y - 5.0, bbox.center.z + 5.0),
                  "POINT", (1.0, 1.0, 1.0, 1.0), 250.),    # front dx
            Light("Lamp SX - Front", (bbox.center.x - 5.0, bbox.center.y - 5.0, bbox.center.z + 5.0),
                  "POINT", (1.0, 1.0, 1.0, 1.0), 250.),    # front sx
            Light("Lamp DX - Rear", (bbox.center.x + 5.0, bbox.center.y + 5.0, bbox.center.z + 5.0),
                  "POINT", (1.0, 1.0, 1.0, 1.0), 250.),    # rear dx
            Light("Lamp SX - Rear", (bbox.center.x - 5.0, bbox.center.y + 5.0, bbox.center.z + 5.0),
                  "POINT", (1.0, 1.0, 1.0, 1.0), 250.)     # rear sx
        )
        for light in lights:
            lamp_data = bpy.data.lights.new(name=light.name, type=light.type)            # new lamp datablock
            lamp_object = bpy.data.objects.new(name=light.name, object_data=lamp_data)   # new lamp object
            environment_collection.objects.link(lamp_object)
            lamp_object.location = light.location
            lamp_object.color = light.colorRGBA
            lamp_data.energy = light.strength   # lamp strength in Watt
        #
        logger.info("Lights added")

    # ==============================================================================================
    @staticmethod
    def init_camera(scene: bpy.types.Scene, camera: bpy.types.Camera, view_layer: bpy.types.ViewLayer) -> None:
        """Init render camera parameters.

        Arguments:
            scene {bpy.types.Scene} -- current scene
            camera {bpy.types.Camera} -- render camera
            view_layer {bpy.types.ViewLayer} -- viewport layer
        """
        logger.info("Initializing camera: %s", camera.name)
        #
        camera.scale[0] = 1.0
        camera.scale[1] = 1.0
        camera.scale[2] = 1.0
        # lens
        camera.data.type = 'PERSP'
        camera.data.lens = 35.0                  # focal length in millimeters
        camera.data.lens_unit = 'MILLIMETERS'
        camera.data.shift_x = 0.000
        camera.data.shift_y = 0.000
        camera.data.clip_start = 0.100
        camera.data.clip_end = 100.0
        # sensor
        camera.data.sensor_width = 32            # sensor width in millimeters
        camera.data.sensor_height = 18           # sensor height in millimeters
        camera.data.sensor_fit = 'HORIZONTAL'
        # display
        camera.data.show_limits = True
        camera.data.display_size = 0.50
        # depth of field
        camera.data.dof.aperture_fstop = 2.8
        camera.data.dof.aperture_blades = 0
        camera.data.dof.aperture_rotation = 0.0
        camera.data.dof.aperture_ratio = 1.0
        camera.data.dof.focus_distance = camera_detect_dof_distance(view_layer, camera, scene)
        #
        logger.info("Camera initialized")

    # ==============================================================================================
    @staticmethod
    def init_effects(scene: bpy.types.Scene, properties: SFMFLOW_AddonProperties) -> None:
        """Initialize global effects.
        Currently motion blur only.

        Arguments:
            scene {bpy.types.Scene} -- current scene
            properties {AddonProperties} -- addon properties
        """
        # --- Motion blur
        scene.cycles.motion_blur_position = 'CENTER'
        scene.render.motion_blur_shutter = properties.motion_blur_shutter

    # ==============================================================================================
    def add_floor(self, scene: bpy.types.Scene) -> None:
        """Add floor to scene.

        Arguments:
            scene {scene} -- blender scene
        """
        logger.info("Adding floor to scene: %s", scene.name)
        #
        plane_size = max(self.scene_bbox.width, self.scene_bbox.height) * 400
        environment_collection = get_environment_collection()
        #
        bpy.ops.mesh.primitive_plane_add(size=plane_size, location=self.scene_bbox.floor_center)
        floor = bpy.context.active_object
        floor.name = "Floor"
        environment_collection.objects.link(floor)
        bpy.context.collection.objects.unlink(floor)   # floor is created in the active collection, unlink and relink
        #
        # setup floor material
        material = bpy.data.materials.new("Floor")
        material.use_nodes = True
        add_floor_material_nodes(material.node_tree, plane_size)
        floor.active_material = material
        #
        logger.info("Walls added")

    # ==============================================================================================
    @staticmethod
    def setup_sky(context: bpy.types.Context) -> None:
        """Setup a procedural sky.
        Inspired by https://blenderartists.org/t/procedural-sky-texture/594259/11

        Arguments:
            context {bpy.types.Context} -- current context
        """
        scene = context.scene
        node_tree = scene.world.node_tree
        nodes = node_tree.nodes
        links = node_tree.links
        nodes.clear()   # clear existing
        #
        # --- output chain
        output = nodes.new("ShaderNodeOutputWorld")
        output.location = Vector((2450, 0))
        add_shader = nodes.new("ShaderNodeAddShader")
        add_shader.location = Vector((2300, 0))
        links.new(add_shader.outputs[0], output.inputs['Surface'])
        #
        # --- input chain
        tex_coord = nodes.new("ShaderNodeTexCoord")
        tex_coord.location = Vector((0, 0))
        normal = nodes.new("ShaderNodeNormal")
        normal.location = Vector((200, 0))
        normal.outputs[0].default_value = Vector((0.0, 0.0, 1.0))
        links.new(tex_coord.outputs['Generated'], normal.inputs['Normal'])
        #
        # --- sun glare
        # normal
        sg_01 = nodes.new("ShaderNodeNormal")
        sg_01.location = Vector((600, -300))
        links.new(tex_coord.outputs['Generated'], sg_01.inputs['Normal'])
        # color ramp
        sg_02 = nodes.new("ShaderNodeValToRGB")
        sg_02.location = Vector((750, -300))
        sg_02.color_ramp.interpolation = 'B_SPLINE'
        c = sg_02.color_ramp.elements[0]
        c.position = 0.95
        c.color = Vector((0, 0, 0, 1))
        c = sg_02.color_ramp.elements[1]
        c.position = 0.995
        c.color = Vector((0, 0, 0, 1))
        sg_02.color_ramp.elements.new(1.0)
        c = sg_02.color_ramp.elements[2]
        c.color = Vector((1, 1, 1, 1))
        links.new(sg_01.outputs['Dot'], sg_02.inputs['Fac'])
        # mix
        sg_03a = nodes.new("ShaderNodeMixRGB")
        sg_03a.location = Vector((1000, -300))
        sg_03a.inputs['Color1'].default_value = Vector((0., 0., 0., 1.))
        sg_03a.inputs['Color2'].default_value = Vector((1., 0.6, 0.07, 1.))
        links.new(sg_02.outputs['Color'], sg_03a.inputs['Fac'])
        # color ramp
        sg_03b = nodes.new("ShaderNodeValToRGB")
        sg_03b.location = Vector((1000, -550))
        sg_03b.color_ramp.interpolation = 'EASE'
        c = sg_03b.color_ramp.elements[0]
        c.position = 0.0
        c.color = Vector((0, 0, 0, 1))
        c = sg_03b.color_ramp.elements[1]
        c.position = 0.05
        c.color = Vector((1, 1, 1, 1))
        links.new(normal.outputs['Dot'], sg_03b.inputs['Fac'])
        # multiply
        sg_04 = nodes.new("ShaderNodeMixRGB")
        sg_04.location = Vector((1250, -300))
        sg_04.blend_type = 'MULTIPLY'
        sg_04.inputs['Fac'].default_value = 1.0
        links.new(sg_03a.outputs['Color'], sg_04.inputs['Color1'])
        links.new(sg_03b.outputs['Color'], sg_04.inputs['Color2'])
        # background
        sg_05 = nodes.new("ShaderNodeBackground")
        sg_05.location = Vector((1400, -300))
        sg_05.inputs['Strength'].default_value = 1.5
        links.new(sg_04.outputs['Color'], sg_05.inputs['Color'])
        # to out
        links.new(sg_05.outputs['Background'], add_shader.inputs[1])
        #
        # --- clouds chain
        # mapping
        cl_01a = nodes.new("ShaderNodeMapping")
        cl_01a.location = Vector((600, 300))
        cl_01a.vector_type = 'POINT'
        pi_2 = 2 * pi
        location = Vector((random() - 0.5, random() - 0.5, random() - 0.5))
        rotation = Vector((random() * pi_2, random() * pi_2, random() * pi_2))
        scale = Vector((1 + random(), 1 + random(), 1 + random()))
        if bpy.app.version >= BlenderVersion.V2_81:  # v2.81+
            cl_01a.inputs['Location'].default_value = location
            cl_01a.inputs['Rotation'].default_value = rotation
            cl_01a.inputs['Scale'].default_value = scale
        else:                                        # v2.80
            cl_01a.translation = location
            cl_01a.rotation = rotation
            cl_01a.scale = scale
        links.new(tex_coord.outputs['Generated'], cl_01a.inputs['Vector'])
        # color ramp
        cl_01b = nodes.new("ShaderNodeValToRGB")
        cl_01b.location = Vector((600, 0))
        cl_01b.color_ramp.interpolation = 'B_SPLINE'
        c = cl_01b.color_ramp.elements[0]
        c.position = 0.0
        c.color = Vector((0.6, 0.6, 0.6, 1))
        c = cl_01b.color_ramp.elements[1]
        c.position = 0.33
        c.color = Vector((0.3, 0.3, 0.3, 1))
        cl_01b.color_ramp.elements.new(1.0)
        c = cl_01b.color_ramp.elements[2]
        c.color = Vector((0.1, 0.1, 0.1, 1))
        links.new(normal.outputs['Dot'], cl_01b.inputs['Fac'])
        # multiply
        cl_02 = nodes.new("ShaderNodeMath")
        cl_02.operation = 'MULTIPLY'
        cl_02.location = Vector((950, 0))
        cl_02.inputs[1].default_value = 15.0
        links.new(cl_01b.outputs['Color'], cl_02.inputs[0])
        # noise texture
        cl_03 = nodes.new("ShaderNodeTexNoise")
        cl_03.location = Vector((1100, 150))
        cl_03.inputs['Detail'].default_value = 16.0
        cl_03.inputs['Distortion'].default_value = 0.0
        links.new(cl_01a.outputs['Vector'], cl_03.inputs['Vector'])
        links.new(cl_02.outputs['Value'], cl_03.inputs['Scale'])
        # color ramp
        cl_04a = nodes.new("ShaderNodeValToRGB")
        cl_04a.location = Vector((1250, 450))
        cl_04a.color_ramp.interpolation = 'LINEAR'
        c = cl_04a.color_ramp.elements[0]
        c.position = 0.0
        c.color = Vector((0, 0, 0, 1))
        c = cl_04a.color_ramp.elements[1]
        c.position = 0.1
        c.color = Vector((1, 1, 1, 1))
        links.new(normal.outputs['Dot'], cl_04a.inputs['Fac'])
        # color ramp
        cl_04b = nodes.new("ShaderNodeValToRGB")
        cl_04b.location = Vector((1250, 150))
        cl_04b.color_ramp.interpolation = 'B_SPLINE'
        c = cl_04b.color_ramp.elements[0]
        c.position = 0.0
        c.color = Vector((0, 0, 0, 1))
        c = cl_04b.color_ramp.elements[1]
        c.position = 0.45
        c.color = Vector((0.01, 0.01, 0.01, 1))
        cl_04b.color_ramp.elements.new(1.0)
        c = cl_04b.color_ramp.elements[2]
        c.position = 0.55
        c.color = Vector((0.2, 0.2, 0.2, 1))
        cl_04b.color_ramp.elements.new(1.0)
        c = cl_04b.color_ramp.elements[3]
        c.position = 0.7
        c.color = Vector((0.45, 0.45, 0.45, 1))
        cl_04b.color_ramp.elements.new(1.0)
        c = cl_04b.color_ramp.elements[4]
        c.position = 0.85
        c.color = Vector((1, 1, 1, 1))
        links.new(cl_03.outputs['Color'], cl_04b.inputs['Fac'])
        # multiply color
        sg_05 = nodes.new("ShaderNodeMixRGB")
        sg_05.location = Vector((1500, 250))
        sg_05.blend_type = 'MULTIPLY'
        sg_05.inputs['Fac'].default_value = 1.0
        links.new(cl_04a.outputs['Color'], sg_05.inputs['Color1'])
        links.new(cl_04b.outputs['Color'], sg_05.inputs['Color2'])
        #
        # --- Sky chain
        # sky texture
        sky_tex = nodes.new("ShaderNodeTexSky")
        sky_tex.location = Vector((1650, 50))
        sky_tex.sky_type = 'HOSEK_WILKIE'   # TODO switch to the new NISHITA in 2.90+ ?
        sky_tex.turbidity = 2.0
        sky_tex.ground_albedo = 0.5
        # mix color
        sc_01 = nodes.new("ShaderNodeMixRGB")
        sc_01.location = Vector((1850, 200))
        sc_01.blend_type = 'MIX'
        sc_01.inputs['Color2'].default_value = Vector((0.490, 0.405, 0.319, 1))
        links.new(sky_tex.outputs['Color'], sc_01.inputs['Color1'])
        links.new(sg_05.outputs['Color'], sc_01.inputs['Fac'])
        # background
        sc_02 = nodes.new("ShaderNodeBackground")
        sc_02.location = Vector((2000, 200))
        sc_02.inputs['Strength'].default_value = 1.5
        links.new(sc_01.outputs['Color'], sc_02.inputs['Color'])
        # to out
        links.new(sc_02.outputs['Background'], add_shader.inputs[0])
        #
        # --- sun driver
        lamp = bpy.data.lights.new("Sun", "SUN")
        lamp.energy = 5.0
        lamp_obj = bpy.data.objects.new("SunDriver", lamp)
        environment_collection = get_environment_collection()
        environment_collection.objects.link(lamp_obj)
        # sun driver
        dr = sky_tex.driver_add("sun_direction")
        # X
        dr[0].driver.expression = 'var'
        var = dr[0].driver.variables.new()
        var.type = 'SINGLE_PROP'
        var.targets[0].id = lamp_obj
        var.targets[0].data_path = 'matrix_world[2][0]'
        # Y
        dr[1].driver.expression = 'var'
        var = dr[1].driver.variables.new()
        var.type = 'SINGLE_PROP'
        var.targets[0].id = lamp_obj
        var.targets[0].data_path = 'matrix_world[2][1]'
        # Z
        dr[2].driver.expression = 'var'
        var = dr[2].driver.variables.new()
        var.type = 'SINGLE_PROP'
        var.targets[0].id = lamp_obj
        var.targets[0].data_path = 'matrix_world[2][2]'
        #
        # --- sun's glare driver
        dr = sg_01.outputs[0].driver_add("default_value")
        # X
        dr[0].driver.expression = 'var'
        var = dr[0].driver.variables.new()
        var.type = 'SINGLE_PROP'
        var.targets[0].id = lamp_obj
        var.targets[0].data_path = 'matrix_world[2][0]'
        # Y
        dr[1].driver.expression = 'var'
        var = dr[1].driver.variables.new()
        var.type = 'SINGLE_PROP'
        var.targets[0].id = lamp_obj
        var.targets[0].data_path = 'matrix_world[2][1]'
        # Z
        dr[2].driver.expression = 'var'
        var = dr[2].driver.variables.new()
        var.type = 'SINGLE_PROP'
        var.targets[0].id = lamp_obj
        var.targets[0].data_path = 'matrix_world[2][2]'
        #
        # --- default sun rotation
        lamp_obj.rotation_mode = "XYZ"
        lamp_obj.rotation_euler = SFMFLOW_OT_init_scene.DEFAULT_SUN_ROTATION

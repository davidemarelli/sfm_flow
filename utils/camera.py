
import logging
from typing import Tuple

import bpy
from mathutils import Vector

from .blender_version import BlenderVersion
from .math import euclidean_distance

logger = logging.getLogger(__name__)


# ==================================================================================================
def get_camera_lookat(camera: bpy.types.Camera) -> Vector:
    """Get the look-at direction of a given camera in blender's reference system.

    Arguments:
        camera {bpy.types.Camera} -- camera object

    Raises:
        NotImplementedError: if multiple TRACK_TO constraint are present

    Returns:
        Vector -- camera's look at direction in blender's reference system
    """
    # if camera has TRACK_TO constraints the look_at direction is not equal to
    # camera.matrix_world.to_quaternion() @ Vector((0.0, 0.0, -1.0))
    #
    constraints = [m for m in camera.constraints if m.type == "TRACK_TO"]
    #
    look_at_target = None
    if constraints:
        if len(constraints) > 1:
            raise NotImplementedError("Handling of multiple TRACK_TO constraint not implemented!")
        look_at_target = constraints[0].target
    #
    camera_lookat = Vector()
    if not look_at_target:
        # if not using a target the camera is looking in its defined direction
        camera_lookat = camera.matrix_world.to_quaternion() @ Vector((0.0, 0.0, -1.0))
    else:
        # if using a target the camera is looking to the target
        camera_lookat = (look_at_target.location - camera.location).normalized()
    #
    return camera_lookat


# ==================================================================================================
def get_camera_up(camera: bpy.types.Camera) -> Vector:
    """Get the up direction of a given camera in blender's reference system.

    Arguments:
        camera {bpy.types.Camera} -- camera object

    Returns:
        Vector -- camera's up direction in blender's reference system
    """
    return camera.matrix_world.to_quaternion() @ Vector((0.0, 1.0, 0.0))


# ==================================================================================================
def get_camera_right(camera: bpy.types.Camera) -> Vector:
    """Get the right direction of a given camera in blender's reference system.

    Arguments:
        camera {bpy.types.Camera} -- camera object

    Returns:
        Vector -- camera's right direction in blender's reference system
    """
    return camera.matrix_world.to_quaternion() @ Vector((1.0, 0.0, 0.0))


# ==================================================================================================
def get_camera_left(camera: bpy.types.Camera) -> Vector:
    """Get the left direction of a given camera in blender's reference system.

    Arguments:
        camera {bpy.types.Camera} -- camera object

    Returns:
        Vector -- camera's left direction in blender's reference system
    """
    return camera.matrix_world.to_quaternion() @ Vector((-1.0, 0.0, 0.0))


# ==================================================================================================
def camera_detect_nearest_intersection(view_layer: bpy.types.ViewLayer, camera: bpy.types.Camera,
                                       scene: bpy.types.Scene) -> Vector:
    """Detect the nearest intersection point in the camera look-at direction.

    Arguments:
        view_layer {bpy.types.ViewLayer} -- view layer
        camera {bpy.types.Camera} -- camera object
        scene {bpy.types.Scene} -- render scene

    Returns:
        Vector -- point of intersection between camera look-at and scene objects.
                  If no intersection found returns camera location. TODO better return infinite?
    """
    camera_lookat = get_camera_lookat(camera)
    if bpy.app.version >= BlenderVersion.V2_91:
        # see https://wiki.blender.org/wiki/Reference/Release_Notes/2.91/Python_API
        view_layer = view_layer.depsgraph
    result, location, *_ = scene.ray_cast(view_layer, camera.location, camera_lookat)
    logger.debug("Nearest intersection for camera %s (location=%s, look_at=%s): found=%s, position=%s",
                 camera.name, camera.location, camera_lookat, result, location)
    if result:
        return location
    else:
        return camera.location


# ==================================================================================================
def camera_detect_dof_distance(view_layer: bpy.types.ViewLayer, camera: bpy.types.Camera,
                               scene: bpy.types.Scene) -> float:
    """Find the depth of field focus distance to the first intersected object in the scene.

    Arguments:
        view_layer {bpy.types.ViewLayer} -- view layer
        camera {bpy.types.Camera} -- camera
        scene {bpy.types.Scene} -- scene

    Returns:
        float -- distance to the intersection
    """
    location = camera_detect_nearest_intersection(view_layer, camera, scene)
    return euclidean_distance(camera.location, location)


# ==================================================================================================
def get_ground_sample_distance(camera: bpy.types.Camera, scene: bpy.types.Scene,
                               ground_level: float = 0.) -> Tuple[float, Tuple[float, float]]:
    """Get the ground sample distance (GSD) and the image footprint.

    The GSD is the size of a pixel of the rendered image at the ground level.
    The image footprint is the size (width and height) of the rendered image at ground level.

    Arguments:
        camera {bpy.types.Camera} -- render camera
        scene {bpy.types.Scene} -- rendered scene

    Keyword Arguments:
        ground_level {float} -- average Z/altitude coordinate of the ground in meters (default: {0.})

    Raises:
        RuntimeError: if the ground is not below the camera
        NotImplementedError: if the pixels in the render image are not squared

    Returns:
        Tuple[float, Tuple[float, float]] -- GSD, Tuple(footprintWidth, footprintHeight)
    """
    sensor_width = camera.data.sensor_width       # mm
    # sensor_height = camera.data.sensor_height   # mm
    focal_length = camera.data.lens               # mm
    altitude = camera.location.z - ground_level   # m
    render_scale = scene.render.resolution_percentage / 100
    img_width = scene.render.resolution_x * render_scale    # px
    img_height = scene.render.resolution_y * render_scale   # px
    #
    if altitude <= 0.:
        raise RuntimeError("Ground isn't below camera! (altitude={}, camera.z={}, ground.z={})".format(
            altitude, camera.location.z, ground_level))
    if not scene.render.pixel_aspect_x == scene.render.pixel_aspect_y == 1.:
        # TODO handle non-square pixels in GSD computation
        raise NotImplementedError("Currently is not possible to handle non-square pixels in GSD computation!")
    #
    gsd = (altitude * sensor_width * 100) / (focal_length * img_width)  # pixel size at ground level in cm
    img_footprint_width = (gsd * img_width) / 100
    img_footprint_height = (gsd * img_height) / 100
    #
    return gsd, (img_footprint_width, img_footprint_height)


# ==================================================================================================
def is_active_object_camera(context: bpy.types.Context) -> bool:
    """Check if the active object is a camera.

    Arguments:
        context {bpy.types.Context} -- current context

    Returns:
        bool -- True iff the active object is a camera object
    """
    return context.active_object and isinstance(context.active_object.data, bpy.types.Camera)

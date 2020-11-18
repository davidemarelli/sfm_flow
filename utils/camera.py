
import logging

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

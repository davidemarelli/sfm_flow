
import logging
from math import atan, cos, pi, tan
from typing import Literal, Tuple

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
def get_camera_fov(camera: bpy.types.Object, scene: bpy.types.Scene) -> Tuple[float, float]:
    """Compute the camera's horizontal and vertical Field of View (FoV).
    The FoV is computed using the focal length and the used sensor size (depends on the rendering
    aspect ratio that can differ from the sensor's one).

    Arguments:
        camera {bpy.types.Object} -- camera object
        scene {bpy.types.Scene} -- scene, used to compute the sensor size crop

    Raises:
        NotImplementedError: if the pixels in the render image are not squared (from get_sensor_size_crop())

    Returns:
        Tuple[float, float] -- horizontal and vertical FoVs in radians
    """
    focal_length = camera.data.lens                      # mm
    sensor_width, sensor_height = get_sensor_size_crop(camera, scene)  # mm
    fov_h = 2 * atan(sensor_width / (2*focal_length))    # horizontal fov
    fov_v = 2 * atan(sensor_height / (2*focal_length))   # vertical fov
    return fov_h, fov_v


# ==================================================================================================
def get_camera_ifov(camera: bpy.types.Object, scene: bpy.types.Scene) -> float:
    """Compute the Instantaneous Field of View (IFOV) of a given camera.

    Arguments:
        camera {bpy.types.Object} -- camera object
        scene {bpy.types.Scene} -- scene, used to get the image resolution to compute the pixel size

    Raises:
        NotImplementedError: if the pixels in the render image are not squared (from get_pixel_size())

    Returns:
        float -- IFOV in radians, same for horizontal and vertical directions
    """
    focal_length = camera.data.lens                  # mm
    pixel_size = get_pixel_size(camera, scene)       # mm
    ifov = 2 * atan(pixel_size / (2*focal_length))   # single pixel fov in radians
    return ifov


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
        NotImplementedError: if the pixels in the render image are not squared or the camera isn't
                             looking towards the ground (alpha >= 90°)

    Returns:
        Tuple[float, Tuple[float, float]] -- GSD in cm, (footprintWidth, footprintHeight) in meters
    """
    if not scene.render.pixel_aspect_x == scene.render.pixel_aspect_y == 1.:
        # TODO handle non-square pixels in GSD computation ?
        raise NotImplementedError("Cannot handle non-square pixels in GSD computation!")
    #
    altitude = camera.location.z - ground_level   # m
    if altitude <= 0.:
        raise RuntimeError(f"Ground isn't below camera! (altitude={altitude}, camera.z={camera.location.z},"
                           " ground.z={ground_level})")
    #
    alpha = Vector((0, 0, -1)).angle(get_camera_lookat(camera))   # angle between nadir direction and camera's look-at
    if alpha >= pi/2:   # alpha >= 90°
        raise RuntimeError("The camera isn't looking towards the ground, cannot compute the GSD!")
    #
    # GSD
    h = altitude * 100  # m to cm
    ifov = get_camera_ifov(camera, scene)
    gsd = h * (tan(alpha + ifov/2) - tan(alpha - ifov/2))   # gsd of the pixel along the look-at vector
    #
    # image footprint
    fov_h, fov_v = get_camera_fov(camera, scene)
    img_footprint_width = altitude * (tan(alpha + fov_h/2) - tan(alpha - fov_h/2))
    img_footprint_height = altitude * (tan(alpha + fov_v/2) - tan(alpha - fov_v/2))
    #
    return gsd, (img_footprint_width, img_footprint_height)


# ==================================================================================================
def get_focal_length_for_gsd(camera: bpy.types.Camera, scene: bpy.types.Scene, gsd: float,
                             ground_level: float = 0.) -> float:
    """Compute the focal length needed to obtain the desired GSD.

    Arguments:
        camera {bpy.types.Camera} -- render camera
        scene {bpy.types.Scene} -- rendered scene
        gsd {float} -- desired size of the pixel at ground level in centimeters

    Keyword Arguments:
        ground_level {float} -- average Z/altitude coordinate of the ground in meters (default: {0.})

    Raises:
        RuntimeError: if the ground is not below the camera
        NotImplementedError: if the pixels in the render image are not squared or the camera isn't
                             looking towards the ground (alpha >= 90°)

    Returns:
        float -- focal length in millimeters
    """
    if not scene.render.pixel_aspect_x == scene.render.pixel_aspect_y == 1.:
        raise NotImplementedError("Cannot handle non-square pixels!")   # TODO handle non-square pixels?
    #
    altitude = camera.location.z - ground_level   # m
    pixel_size = get_pixel_size(camera, scene)    # mm
    #
    if altitude <= 0.:
        raise RuntimeError(f"Ground isn't below camera! (altitude={altitude}, camera.z={camera.location.z},"
                           " ground.z={ground_level})")
    #
    alpha = Vector((0, 0, -1)).angle(get_camera_lookat(camera))   # angle between nadir direction and camera's look-at
    if alpha >= pi/2:   # alpha >= 90°
        raise RuntimeError("The camera isn't looking towards the ground, cannot compute the GSD!")
    #
    # get focal length for desired gsd
    h = altitude / cos(alpha)
    # FIXME current formula is an approximation, fix?
    focal_length = (h * pixel_size * 100) / (gsd * cos(alpha))  # get the focal length that obtains the desired gsd
    #
    return focal_length


# ==================================================================================================
def get_pixel_size(camera: bpy.types.Camera, scene: bpy.types.Scene) -> float:
    """Compute the pixel size on the sensor for the given camera.

    Arguments:
        camera {bpy.types.Camera} -- camera object
        scene {bpy.types.Scene} -- scene, used to get the render image resolution

    Raises:
        NotImplementedError: if the pixels in the render image are not squared

    Returns:
        float -- pixels size on the camera sensor in millimeters
    """
    sensor_width = camera.data.sensor_width       # mm
    sensor_height = camera.data.sensor_height     # mm
    sensor_fit = camera.data.sensor_fit           # type: Literal['HORIZONTAL', 'VERTICAL', 'AUTO']
    render_scale = scene.render.resolution_percentage / 100
    img_width = scene.render.resolution_x * render_scale    # px
    img_height = scene.render.resolution_y * render_scale   # px

    if not scene.render.pixel_aspect_x == scene.render.pixel_aspect_y == 1.:
        raise NotImplementedError("Currently is not possible to handle non-square pixels!")

    # compute pixel size on the sensor (in millimeters)
    if sensor_fit == 'HORIZONTAL':
        pixel_size = sensor_width / img_width
    elif sensor_fit == 'VERTICAL':
        pixel_size = sensor_height / img_height
    else:   # 'AUTO'
        if sensor_width / img_width <= sensor_height / img_height:
            pixel_size = sensor_width / img_width
        else:
            pixel_size = sensor_height / img_height

    return pixel_size


# ==================================================================================================
def get_sensor_size_crop(camera: bpy.types.Camera, scene: bpy.types.Scene) -> Tuple[float, float]:
    """Compute the used sensor size of the given camera for the current image rendering resolution.

    Arguments:
        camera {bpy.types.Camera} -- camera object
        scene {bpy.types.Scene} -- scene, used to get the render image resolution

    Raises:
        NotImplementedError: if the pixels in the render image are not squared

    Returns:
        Tuple[float, float] -- size of the camera sensor in millimeters (only the used portion for
                               the current rendering resolution)
    """
    sensor_width = camera.data.sensor_width       # mm
    sensor_height = camera.data.sensor_height     # mm
    sensor_fit = camera.data.sensor_fit           # type: Literal['HORIZONTAL', 'VERTICAL', 'AUTO']
    render_scale = scene.render.resolution_percentage / 100
    img_width = scene.render.resolution_x * render_scale    # px
    img_height = scene.render.resolution_y * render_scale   # px

    if not scene.render.pixel_aspect_x == scene.render.pixel_aspect_y == 1.:
        raise NotImplementedError("Currently is not possible to handle non-square pixels!")

    # compute used sensor size of the current image size
    if sensor_fit == 'HORIZONTAL':
        pixel_size = sensor_width / img_width
        width_crop_size = sensor_width
        height_crop_size = pixel_size * img_height
    elif sensor_fit == 'VERTICAL':
        pixel_size = sensor_height / img_height
        height_crop_size = sensor_height
        width_crop_size = pixel_size * img_width
    else:   # 'AUTO'
        if sensor_width / img_width <= sensor_height / img_height:
            pixel_size = sensor_width / img_width
            width_crop_size = sensor_width
            height_crop_size = pixel_size * img_height
        else:
            pixel_size = sensor_height / img_height
            height_crop_size = sensor_height
            width_crop_size = pixel_size * img_width

    assert width_crop_size <= sensor_width
    assert height_crop_size <= sensor_height

    return width_crop_size, height_crop_size


# ==================================================================================================
def is_active_object_camera(context: bpy.types.Context) -> bool:
    """Check if the active object is a camera.

    Arguments:
        context {bpy.types.Context} -- current context

    Returns:
        bool -- True iff the active object is a camera object
    """
    return hasattr(context, "active_object") and context.active_object \
        and isinstance(context.active_object.data, bpy.types.Camera)


import logging
from math import cos, degrees, pi, sin, sqrt
from random import random, uniform
from typing import List, Optional, Tuple

import bpy
from mathutils import Quaternion, Vector

from .camera import camera_detect_nearest_intersection
from .math import euclidean_distance
from .object import get_environment_collection

logger = logging.getLogger(__name__)


RANDOMIZE_PERCENT = 0.05


# ==================================================================================================
def build_camera_point(x: float, y: float, z: float, randomize: bool) -> Vector:
    """Given the coordinates and optional randomization flag returns a point in form of {Vector}.

    Arguments:
        x {float} -- X coordinate
        y {float} -- Y coordinate
        z {float} -- Z coordinate
        randomize {bool} -- if {True} the point is randomized +/- the percentage defined by `RANDOMIZE_PERCENT`

    Returns:
        Vector -- generated point
    """
    if randomize:
        p = Vector((x * uniform(1. - RANDOMIZE_PERCENT, 1. + RANDOMIZE_PERCENT),
                    y * uniform(1. - RANDOMIZE_PERCENT, 1. + RANDOMIZE_PERCENT),
                    z * uniform(1. - RANDOMIZE_PERCENT, 1. + RANDOMIZE_PERCENT)))
    else:
        p = Vector((x, y, z))
    return p


# ==================================================================================================
def get_last_keyframe(obj: bpy.types.Object) -> Optional[int]:
    """Get last keyframe set (biggest frame number on the timeline) for a given object.

    Arguments:
        obj {Object} -- scene object

    Returns:
        Optional[int] -- last keyframe if any, {None} otherwise
    """
    last_keyframe = None
    anim = obj.animation_data
    if anim is not None and anim.action is not None:
        for fc in anim.action.fcurves:
            for keyframe in fc.keyframe_points:
                x, _ = keyframe.co
                if not last_keyframe or x > last_keyframe:
                    last_keyframe = x
    return last_keyframe


# ==================================================================================================
def is_keyframe(obj: bpy.types.Object, frame_number: int, keyframe_type: str = None) -> bool:
    """Check if an object has a keyframe set at a given frame. Optionally restrict to keyframe type.

    Arguments:
        obj {bpy.types.Object} -- blender object
        frame_number {int} -- frame to test

    Keyword Arguments:
        keyframe_type {str} -- type of keyframe (default: {None})

    Returns:
        bool -- true only if keyframe
    """
    anim = obj.animation_data
    if anim is not None and anim.action is not None:
        for fc in anim.action.fcurves:
            if not keyframe_type or fc.data_path == keyframe_type:
                return frame_number in (round(p.co.x) for p in fc.keyframe_points)
    return False


# ==================================================================================================
def get_track_to_constraint_target(obj: bpy.types.Object) -> Tuple[Optional[bpy.types.Object],
                                                                   Optional[bpy.types.Constraint]]:
    """Search for the TRACK_TO constraint target of a given object.

    Arguments:
        obj {bpy.types.Object} -- where to search the constraint

    Returns:
        Tuple[Optional[bpy.types.Object], Optional[bpy.types.Constraint]] --
            TRACK_TO target if any, {None} otherwise.
            TRACK_TO constraint if any, {None} otherwise.
    """
    if obj.constraints:
        for c in obj.constraints:
            if c.type == 'TRACK_TO':
                return c.target, c
    return None, None


# ==================================================================================================
def set_camera_target(camera: bpy.types.Camera, target_location: Vector, target_name: str = "") -> None:
    """Set a Track_TO constraint target for a camera. Constraint is not re-created if already exists.

    Arguments:
        camera {bpy.types.Camera} -- render camera
        target_location {Vector} -- location of the EMPTY target

    Keyword Arguments:
        target_name {str} -- name for the EMPTY target
    """
    target, _ = get_track_to_constraint_target(camera)
    if not target:
        target = bpy.data.objects.new("EMPTY", None)
        environment_collection = get_environment_collection()
        environment_collection.objects.link(target)
        tt = camera.constraints.new(type='TRACK_TO')
        tt.target = target
        tt.track_axis = 'TRACK_NEGATIVE_Z'
        tt.up_axis = 'UP_Y'
    target.name = target_name
    target.location = target_location
    return target


# ==================================================================================================
def set_camera_focus_to_intersection(view_layer: bpy.types.ViewLayer, camera: bpy.types.Camera,
                                     scene: bpy.types.Scene, frame_number: int) -> None:
    """Given a camera sets its focus distance to the nearest object intersection point.

    Arguments:
        view_layer {bpy.types.ViewLayer} -- desired view layer
        camera {bpy.types.Camera} -- camera object
        scene {bpy.types.Scene} -- scene
        frame_number {int} -- frame number in scene
    """
    target = None
    if not camera.data.dof.focus_object:
        target = bpy.data.objects.new("EMPTY", None)
        target.name = camera.name + " Focus target"
        environment_collection = get_environment_collection()
        environment_collection.objects.link(target)
        camera.data.dof.focus_object = target
    else:
        target = camera.data.dof.focus_object
    #
    intersection_point = camera_detect_nearest_intersection(view_layer, camera, scene)
    target.location = intersection_point
    target.keyframe_insert(data_path="location", frame=frame_number)


# ==================================================================================================
def sample_points_on_hemisphere(center: Vector = Vector((0, 0, 0)), radius: float = 1,
                                samples: int = None, randomize: bool = False) -> List[Vector]:
    """Sample points on an hemisphere.

    Keyword Arguments:
        center {Vector} -- hemisphere center (default: {Vector((0, 0, 0))})
        radius {float} -- hemisphere radius (default: {1})
        samples {int} -- number of samples (default: {None})
        randomize {bool} -- if {True} the sample distances are randomized, otherwise are kept equal (default: {False})

    Returns:
        List[Vector] -- list of vertices on the hemisphere
    """

    unit_point_count = 10   # default number of points radius=1 hemisphere
    if not samples:
        samples = int(radius * unit_point_count)

    points = []
    offset = - 1.0 / samples
    increment = pi * (3.0 - sqrt(5.0))   # golden angle

    for i in range(samples):
        z = ((i * offset) + 1) + (offset / 2)

        r = sqrt(1 - z**2)
        phi = i * increment

        x = cos(phi) * r
        y = sin(phi) * r

        p = build_camera_point(x * radius + center.x,
                               y * radius + center.y,
                               z * radius + center.z,
                               randomize)
        points.append(p)

    return points


# ==================================================================================================
def sample_points_on_conical_helix(start_center: Vector, start_point: Vector, turns: int, points_per_turn: int,
                                   height: float, height_type: str = "TOTAL", end_radius: float = None,
                                   randomize: bool = False) -> List[Vector]:
    """Create a list of vertices sampled on a conical helix.

    Arguments:
        start_center {Vector} -- starting center point of the helix
        start_point {Vector} -- first point of the helix
        turns {int} -- number of turns
        points_per_turn {int} -- number of points on each turn
        height {float} -- can be the `TOTAL` or `TURN` height, depends on `height_type`

    Keyword Arguments:
        end_radius {float} -- OPTIONAL ending radius, if `None` the same as the start radius is used (default: {None})
        height_type {str} -- type of the `height` argument, `TOTAL` for total height or `TURN` for turn height
                             (default: {"TOTAL"})
        randomize {bool} -- if {True} the position is randomized around the correct one (default: {False})

    Raises:
        ValueError: If `height_type` is invalid

    Returns:
        List[Vector] -- list of vertices on the helix
    """
    start_radius = euclidean_distance(start_center, start_point)

    # adjust total height
    if height_type == "TOTAL":  # if provided height is already total height
        total_height = height
    elif height_type == "TURN":  # if provided height is single turn height
        total_height = turns * height
    else:
        msg = "Unknown height type: {}".format(height_type)
        logger.fatal(msg)
        raise ValueError(msg)
    #
    radius_diff = end_radius - start_radius if end_radius else 0.
    num_of_points = turns * points_per_turn
    z = start_point.z  # start Z coordinate
    #
    pts = []
    c_point_num = 0   # current point number
    y_offset = 0.
    x_offset = 0.
    a_offset = Vector((0, 1, 0)).angle((start_point-start_center))
    for _ in range(turns):
        for i in range(points_per_turn):
            a = 2 * pi * (i / points_per_turn) + a_offset   # point rotation angle

            progress_percent = c_point_num / num_of_points
            radius = start_radius + radius_diff * progress_percent

            x = sin(a) * radius
            y = cos(a) * radius

            if c_point_num != 0:
                z += (total_height / turns) / points_per_turn
            else:
                # for the first point get the offset
                x_offset = start_point.x - x
                y_offset = start_point.y - y
            y += y_offset
            x += x_offset

            pts.append(build_camera_point(x, y, z, randomize))
            c_point_num += 1
    return pts


# ==================================================================================================
def sample_points_on_helix(start_center: Vector, start_point: Vector, turns: int, points_per_turn: int,
                           height: float, height_type: str = "TOTAL", randomize: bool = False) -> List[Vector]:
    """Create a list of vertices sampled on a conical helix.

    Arguments:
        start_point {Vector} -- first point of the helix
        turns {int} -- number of turns
        radius {float} -- helix radius
        points_per_turn {int} -- number of points on each turn
        height {float} -- can be the `TOTAL` or `TURN` height, depends on `height_type`

    Keyword Arguments:
        height_type {str} -- type of the `height` argument, `TOTAL` for total height or `TURN` for turn height
                             (default: {"TOTAL"})
        randomize {bool} -- if {True} the position is randomized around the correct one (default: {False})

    Returns:
        List[Vector] -- list of vertices on the helix
    """
    return sample_points_on_conical_helix(start_center=start_center, start_point=start_point, turns=turns,
                                          points_per_turn=points_per_turn, height=height, height_type=height_type,
                                          randomize=randomize)


# ==================================================================================================
def sample_points_on_circle(center: Vector, start_point: Vector, points_count: int,
                            randomize: bool = False) -> List[Vector]:
    """Create a list of vertices sampled on a circle.

    Arguments:
        center {Vector} -- center point of the circle
        start_point {Vector} -- first point of the circle
        points_count {int} -- number of points to be sampled on the circle

    Keyword Arguments:
        randomize {bool} -- if {True} the position is randomized around the correct one (default: {False})

    Returns:
        List[Vector] -- list of vertices on the circle
    """
    radius = euclidean_distance(center, start_point)
    #
    z = start_point.z  # start z coordinate
    #
    pts = []
    c_point_num = 0   # current point number (counter)
    y_offset = 0.
    x_offset = 0.
    a_offset = Vector((0, 1, 0)).angle((start_point-center))
    for i in range(points_count):
        a = 2 * pi * (i / points_count) + a_offset   # point rotation angle

        x = sin(a) * radius
        y = cos(a) * radius

        if c_point_num == 0:
            # for the first point get the offset
            x_offset = start_point.x - x
            y_offset = start_point.y - y
        y += y_offset
        x += x_offset

        pts.append(build_camera_point(x, y, z, randomize))
        c_point_num += 1

    return pts


# ==================================================================================================
def sun_animation_points(gravity_direction: Vector, north_direction: Vector, scene_bbox: Vector,
                         radius: float, points_count: int) -> List[Vector]:
    """Sample sun lamp position points.

    Arguments:
        gravity_direction {Vector} -- world's gravity direction vector
        north_direction {Vector} -- world's north direction vector
        scene_center {Vector} -- current scene center
        radius {float} -- radius of the animation
        points_count {int} -- desired number of points

    Raises:
        ValueError: if gravity and north directions aren't orthogonal

    Returns:
        List[Vector] -- list of animation points
    """

    # TODO add more realistic sun paths using geolocation and seasons ?

    # sanity check: axes must be orthogonal
    angle = round(gravity_direction.angle(north_direction), 2)
    if angle != round((pi/2), 2):
        msg = "`gravity_direction` and `north_direction` aren't orthogonal (angle={})!".format(degrees(angle))
        logger.error(msg)
        raise ValueError(msg)

    center = scene_bbox.floor_center  # scene_center
    # get the half-vector
    h = - gravity_direction - north_direction
    h.normalize()
    # get the rotation axis
    axis = h.copy()
    axis.rotate(Quaternion(north_direction.cross(gravity_direction), pi/2))

    b = h.copy()
    b.rotate(Quaternion(axis, pi/2))

    pts = []
    for i in range(points_count * 2):
        theta = 2 * pi * (i / (points_count*2))

        # circle
        x = center.x + radius * cos(theta) * b.x + radius * sin(theta) * h.x
        y = center.y + radius * cos(theta) * b.y + radius * sin(theta) * h.y
        z = center.z + radius * cos(theta) * b.z + radius * sin(theta) * h.z
        if z > scene_bbox.z_min:
            continue

        p = Vector((x, y, z)) - center
        pts.append(p)
        #bpy.ops.mesh.primitive_uv_sphere_add(radius=0.01, location=p)

    return pts


# ==================================================================================================
def animate_motion_blur(scene: bpy.types.Scene, blur_probability: float, shutter: float) -> None:
    """Animate the motion blur in the scene's render range.

    Arguments:
        scene {bpy.types.Scene} -- render scene
        blur_probability {float} -- probability of a frame to have motion blur, in range [0-1]
        shutter {float} -- shutter value for motion blur generation
    """
    animate_motion_blur_clear(scene)
    for frame_number in range(scene.frame_start, scene.frame_end + 1):
        if random() < blur_probability:   # blur
            scene.render.motion_blur_shutter = shutter  # shutter time
            scene.render.keyframe_insert("motion_blur_shutter", frame=frame_number)
        else:                             # no blur
            scene.render.motion_blur_shutter = 0.
            scene.render.keyframe_insert("motion_blur_shutter", frame=frame_number)


# ==================================================================================================
def animate_motion_blur_clear(scene: bpy.types.Scene) -> None:
    """Clear the motion blur animation in the scene's render range.

    Arguments:
        scene {bpy.types.Scene} -- render scene
    """
    frame_backup = scene.frame_current
    for frame_number in range(scene.frame_start, scene.frame_end + 1):
        scene.frame_set(frame_number)
        scene.render.keyframe_delete("motion_blur_shutter")
    scene.frame_set(frame_backup)

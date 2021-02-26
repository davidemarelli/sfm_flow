
import logging
from typing import List, Tuple

import bpy
import bpy_extras.mesh_utils
import numpy as np
from mathutils import Vector

logger = logging.getLogger(__name__)

SFMFLOW_COLLECTIONS = (
    "SFMFLOW_Reconstructions", "SfM_Reconstructions",
    "SFMFLOW_Environment", "SfM_Environment",
    "SFMFLOW_GCPs", "SFMFLOW_cameras"
)


# ==================================================================================================
def get_collection(name: str, previous_name: str = None, create: bool = True) -> bpy.types.Collection:
    """Get the desired collection, create it if does not exists.

    Arguments:
        name {str} -- name of the collection

    Keyword Arguments:
        previous_name {str} -- name of the collection in previous SfM Flow versions (default: {None})
        create {bool} -- when True creates the collection if it does not exist (default: {True})

    Returns:
        bpy.types.Collection -- collection of object data-blocks
    """
    recon_collection = None
    if previous_name is not None:   # try to get the old-named collection
        recon_collection = bpy.data.collections.get(previous_name)
    if not recon_collection:        # try to get the collection
        recon_collection = bpy.data.collections.get(name)
    if (not recon_collection) and create:        # if none create the collection
        recon_collection = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(recon_collection)
        logger.info("Created collection `%s`", name)
    return recon_collection


# ==================================================================================================
def get_reconstruction_collection() -> bpy.types.Collection:
    """Get the `SFMFLOW_Reconstructions` collection, create it if does not exists.

    Returns:
        bpy.types.Collection -- Reconstructions collection
    """
    return get_collection("SFMFLOW_Reconstructions", previous_name="SfM_Reconstructions")


# ==================================================================================================
def get_environment_collection() -> bpy.types.Collection:
    """Get the `SFMFLOW_Environment` collection, create it if does not exists.

    Returns:
        bpy.types.Collection -- Environment collection
    """
    return get_collection("SFMFLOW_Environment", previous_name="SfM_Environment")


# ==================================================================================================
def get_gcp_collection(create: bool = True) -> bpy.types.Collection:
    """Get the `SFMFLOW_GCPs` collection, create it if does not exists.

    Keyword Arguments:
        create {bool} -- when True creates the collection if it does not exist (default: {True})

    Returns:
        bpy.types.Collection -- GCPs collection
    """
    return get_collection("SFMFLOW_GCPs", create=create)


# ==================================================================================================
def get_cameras_collection(create: bool = True) -> bpy.types.Collection:
    """Get the `SFMFLOW_cameras` collection, create it if does not exists.

    Keyword Arguments:
        create {bool} -- when True creates the collection if it does not exist (default: {True})

    Returns:
        bpy.types.Collection -- Cameras collection
    """
    return get_collection("SFMFLOW_cameras", create=create)


# ==================================================================================================
def get_objs(scene: bpy.types.Scene, exclude_collections: Tuple[str] = None, mesh_only: bool = True
             ) -> List[bpy.types.Object]:
    """Get all objects in the given scene. Eventually filter by type and collections.

    Arguments:
        scene {bpy.types.Scene} -- scene containing the objects

    Keyword Arguments:
        exclude_collections {List[str]} -- list of group names to exclude from search (default: {None})
        mesh_only {bool} -- if {True} count only `MESH`, `CURVE`, `SURFACE` objects (default: {True})

    Returns:
        List[bpy.types.Object] -- list of scene objects
    """
    objs = []
    for obj in scene.objects:
        exclude = False
        for uc in obj.users_collection:
            if ((exclude_collections is not None) and (uc.name in exclude_collections)) or \
                    (mesh_only and (obj.type not in ['MESH', 'CURVE', 'SURFACE'])):
                exclude = True
                break
        if not exclude:
            objs.append(obj)
    return objs


# ==================================================================================================
def sample_points_on_mesh(objects: bpy.types.Object, density: int = 200) -> List[Vector]:
    """Return a sampled point cloud on the given objects list.

    Arguments:
        objects {bpy.types.Object} -- objects on which sample to points

    Keyword Arguments:
        density {int} -- density of the point sampling (default: {200})

    Returns:
        List[Vector] -- list of sampled points
    """
    points = []
    for obj in objects:
        logger.info("Sampling gt points on mesh '%s'...", obj.name)
        obj_data = obj.data
        if not obj_data.loop_triangles:
            obj_data.calc_loop_triangles()
        mean_area = 0.
        if obj_data.loop_triangles:
            for lt in obj_data.loop_triangles:
                mean_area += lt.area
            mean_area /= len(obj_data.loop_triangles)
        sample_count = int(mean_area * density)
        if sample_count < 1:
            logger.debug("sample_count < 1, forcing one sample per triangle.")
            sample_count = 1
        pts = bpy_extras.mesh_utils.triangle_random_points(sample_count, obj_data.loop_triangles)
        points += [obj.matrix_world @ p for p in pts]
        logger.info("Sampled %i points on mesh '%s'", len(points), obj.name)
    return points


# ==================================================================================================
def is_active_object_reconstruction(context: bpy.types.Context = None) -> bool:
    """Check if the current active object in the 3D view layer is a reconstruction handle.

    Keyword Arguments:
        context {bpy.types.Context} -- current context. {bpy.context} is used if {None} is provided. (default: {None})

    Returns:
        bool -- {True} if the active object is a reconstruction, {False} otherwise.
    """
    if context:
        obj = context.view_layer.objects.active
    else:
        obj = bpy.context.view_layer.objects.active if bpy.context.view_layer is not None else None
    return (obj is not None) and ('sfmflow_model_uuid' in obj) and obj.select_get()


# ==================================================================================================
def show_motion_path(obj: bpy.types.Object, scene: bpy.types.Scene) -> None:
    """Show the motion path of an object.

    Arguments:
        obj {bpy.types.Object} -- an object of a scene
        scene {bpy.types.Scene} -- scene containing the object
    """
    if not obj.motion_path:
        selected_objs = bpy.context.selected_objects
        bpy.ops.object.select_all(action='DESELECT')
        obj.select_set(True)
        #
        bpy.ops.object.paths_calculate(start_frame=scene.frame_start, end_frame=scene.frame_end)
        motion_path = obj.motion_path
        motion_path.lines = False
        motion_path.color = Vector((1, 0, 0))  # Red
        motion_path.use_custom_color = True
        motion_path_viz = obj.animation_visualization.motion_path
        motion_path_viz.show_keyframe_numbers = False
        motion_path_viz.show_keyframe_highlight = False
        #
        bpy.ops.object.select_all(action='DESELECT')
        list(map(lambda o: o.select_set(True), selected_objs))  # restore selection
    elif obj.motion_path.is_modified:
        selected_objs = bpy.context.selected_objects
        bpy.ops.object.select_all(action='DESELECT')
        obj.select_set(True)
        #
        bpy.ops.object.paths_update()
        #
        bpy.ops.object.select_all(action='DESELECT')
        list(map(lambda o: o.select_set(True), selected_objs))  # restore selection


# ==================================================================================================
def hide_motion_path(obj: bpy.types.Object) -> None:
    """Show the motion path of an object.

    Arguments:
        obj {bpy.types.Object} -- an object of a scene
    """
    if obj.name in bpy.data.objects:  # ensure that obj still exists
        selected_objs = bpy.context.selected_objects
        bpy.ops.object.select_all(action='DESELECT')
        obj.select_set(True)
        bpy.ops.object.paths_clear(only_selected=True)
        #
        # restore selection
        bpy.ops.object.select_all(action='DESELECT')
        list(map(lambda o: o.select_set(True), selected_objs))


# ==================================================================================================
def get_average_z_coord(scene: bpy.types.Scene, exclude_collections: Tuple[str] = None) -> float:
    """Compute the average global Z coordinate of the given scene as the average global Z coordinate of the vertices.

    Arguments:
        scene {bpy.types.Scene} -- scene to compute the average Z

    Keyword Arguments:
        exclude_collections {Tuple[str]} -- list of collection names to exclude from obj search (default: {None})

    Returns:
        float -- average Z coordinate in the global coordinate reference system
    """
    objs = get_objs(scene, exclude_collections=exclude_collections, mesh_only=True)
    #
    v_count = 0
    z_total = 0
    for obj in objs:
        mesh = obj.data
        count = len(mesh.vertices)
        v_count += count
        verts = np.empty(count * 3, dtype=np.float32)
        mesh.vertices.foreach_get('co', verts)   # vertices in local coordinates
        # move to global coords
        verts_4 = np.empty((count, 4), dtype=np.float32)
        verts_4[:, -1] = 1.
        verts_4[:, :-1] = verts.reshape((count, 3))   # move to homogeneous coords
        verts_4 = np.einsum('ij,aj->ai', np.array(obj.matrix_world), verts_4)   # matrix_world.dot(verts_4)
        verts = verts_4[:, :-1] / verts_4[:, [-1]]    # back to cartesian coords
        z_total += np.sum(verts[:, 2])
    #
    z_average = z_total / v_count
    return z_average

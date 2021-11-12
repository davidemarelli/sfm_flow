
import logging
from math import log10

import bpy
from mathutils import Vector

logger = logging.getLogger(__name__)


# ==================================================================================================
def setup_depth_export(scene: bpy.types.Scene, out_basepath: str = "//render_depth/",
                       render_camera_name: str = None) -> None:
    """Setup compositor nodes for depth images export.
    For each rendered image 2 additional float32 OpenEXR files will be exported in the given output basepath:
       - <camera name>_depth_normalized_<frame number>.exr containing the normalized [0-1] depth for each pixel.
       - <camera name>_depth_<frame number>.exr containing the raw [0-<clip distance>] depth for each pixel.
         The unit of the depth value is the same as the one configured for the scene (eg. meters, inches, ...).

    This function can be called multiple times to change the camera name and/or the out basepath.
    If a depth setup already exists it will be reused.

    Arguments:
        scene {bpy.types.Scene} -- the scene for which to save the depth files during rendering.

    Keyword Arguments:
        out_basepath {str} -- base output folder for the depth exr files (default: {"//render_depth/"})
        render_camera_name {str} -- name of the camera used for rendering. This name is used as a prefix for
                                    the exr filenames (default: {None})
    """
    if render_camera_name is None:
        render_camera_name = scene.camera.name + '_' if scene.camera is not None else ''
    else:
        render_camera_name += '_'
    render_camera_name = bpy.path.clean_name(render_camera_name, replace='-')
    #
    scene.use_nodes = True
    node_tree = scene.node_tree
    nodes = node_tree.nodes
    nodes_location = Vector((0, 0))
    #
    digits = int(log10(scene.frame_end)) + 1
    filename_digits = '#' * digits   # frame number
    #
    if not 'SFMFLOW_depth_render_layers' in nodes:
        depth_in_layers = nodes.new('CompositorNodeRLayers')
        depth_in_layers.location = nodes_location + Vector((0, 0))
        depth_in_layers.name = 'SFMFLOW_depth_render_layers'
        depth_in_layers.label = "SFMFLOW depth render layers"
    else:
        logger.debug("Re-using 'SFMFLOW_depth_render_layers'")
        depth_in_layers = nodes['SFMFLOW_depth_render_layers']
    #
    if not 'SFMFLOW_depth_normalize' in nodes:
        depth_normalize = nodes.new('CompositorNodeNormalize')
        depth_normalize.location = nodes_location + Vector((300, 0))
        depth_normalize.name = 'SFMFLOW_depth_normalize'
        depth_normalize.label = "SFMFLOW depth normalize"
    else:
        logger.debug("Re-using 'SFMFLOW_depth_normalize'")
        depth_normalize = nodes['SFMFLOW_depth_normalize']
    node_tree.links.new(depth_in_layers.outputs['Depth'], depth_normalize.inputs['Value'])
    #
    if not 'SFMFLOW_depth_normalized_out' in nodes:
        depth_normalized_out = nodes.new('CompositorNodeOutputFile')
        depth_normalized_out.location = nodes_location + Vector((500, 0))
        depth_normalized_out.width = 400
        depth_normalized_out.name = 'SFMFLOW_depth_normalized_out'
        depth_normalized_out.label = "SFMFLOW depth normalized out"
        depth_normalized_out.format.file_format = 'OPEN_EXR'
        depth_normalized_out.format.color_mode = 'RGB'
        depth_normalized_out.format.color_depth = '32'
        depth_normalized_out.format.exr_codec = 'ZIP'
        depth_normalized_out.format.use_zbuffer = False
    else:
        logger.debug("Re-using 'SFMFLOW_depth_normalized_out'")
        depth_normalized_out = nodes['SFMFLOW_depth_normalized_out']
    depth_normalized_out.base_path = out_basepath
    # depth_normalized_out.inputs[0].name = "Depth_Normalized_"
    depth_normalized_out.file_slots[0].path = filename_digits + '_' + render_camera_name + "depth_normalized"
    node_tree.links.new(depth_normalize.outputs['Value'], depth_normalized_out.inputs['Image'])
    #
    if not 'SFMFLOW_depth_out' in nodes:
        depth_out = nodes.new('CompositorNodeOutputFile')
        depth_out.location = nodes_location + Vector((500, -150))
        depth_out.width = 400
        depth_out.name = 'SFMFLOW_depth_out'
        depth_out.label = "SFMFLOW depth out"
        depth_out.format.file_format = 'OPEN_EXR'
        depth_out.format.color_mode = 'RGB'
        depth_out.format.color_depth = '32'
        depth_out.format.exr_codec = 'ZIP'
        depth_out.format.use_zbuffer = False
    else:
        logger.debug("Re-using 'SFMFLOW_depth_out'")
        depth_out = nodes['SFMFLOW_depth_out']
    depth_out.base_path = out_basepath
    # depth_out.inputs[0].name = "Depth_"
    depth_out.file_slots[0].path = filename_digits + '_' + render_camera_name + "depth"
    node_tree.links.new(depth_in_layers.outputs['Depth'], depth_out.inputs[0])


# ==================================================================================================
def remove_depth_export(scene: bpy.types.Scene) -> None:
    """Remove an existing depth export compositor nodes setup.
    If depth export setup exists no changes are done.

    Arguments:
        scene {bpy.types.Scene} -- scene from which delete the depth export setup.
    """
    if scene.use_nodes:
        nodes = scene.node_tree.nodes
        if 'SFMFLOW_depth_render_layers' in nodes:
            nodes.remove(nodes['SFMFLOW_depth_render_layers'])
        if 'SFMFLOW_depth_normalize' in nodes:
            nodes.remove(nodes['SFMFLOW_depth_normalize'])
        if 'SFMFLOW_depth_normalized_out' in nodes:
            nodes.remove(nodes['SFMFLOW_depth_normalized_out'])
        if 'SFMFLOW_depth_out' in nodes:
            nodes.remove(nodes['SFMFLOW_depth_out'])

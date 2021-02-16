
import os
from math import log10
from typing import Tuple

import bpy


# ==================================================================================================
def set_blender_output_path(base_path: str, scene: bpy.types.Scene, camera: bpy.types.Camera = None) -> None:
    """Set the blender render output path for a given scene, frame and camera.
    This allow to build an image filename that contains information about the frame number and the camera name.

    Arguments:
        base_path {str} -- bas output folder
        scene {bpy.types.Scene} -- scene rendered

    Keyword Arguments:
        camera {bpy.types.Camera} -- render camera, if None the render output path is set to the
                                     base folder only (default: {None})
    """
    if not camera:
        scene.render.filepath = base_path
    else:
        digits = int(log10(scene.frame_end)) + 1
        filename = '#' * digits   # frame number
        filename += '_' + bpy.path.clean_name(camera.name, replace='-')   # camera name
        path = os.path.join(base_path, filename)
        scene.render.filepath = path


# ==================================================================================================
def get_render_image_filename(camera: bpy.types.Camera, scene: bpy.types.Scene,
                              frame: int = None) -> Tuple[str, str]:
    """Get the filename and filepath of the frame rendered by the given camera.
    If the frame is not specified the current one is used.

    Arguments:
        camera {bpy.types.Camera} -- camera that renders the image
        scene {bpy.types.Scene} -- current scene

    Keyword Arguments:
        frame {int} -- frame number, if None the current frame is (default: {None})

    Returns:
        Tuple[str, str] -- filename and filepath of the rendered image
    """
    set_blender_output_path(scene.sfmflow.output_path, scene, camera)
    image_filepath = scene.render.frame_path(frame=frame)
    image_filename = bpy.path.basename(image_filepath)
    set_blender_output_path(scene.sfmflow.output_path, scene)
    return image_filename, image_filepath

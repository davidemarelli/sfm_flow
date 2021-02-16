
from typing import Iterable as _Iterable

from bpy.utils import register_class as _register_class
from bpy.utils import unregister_class as _unregister_class

from .animation import *
from .blender_version import BlenderVersion
from .camera import *
from .gt_writer import GroundTruthWriter
from .math import *
from .object import *
from .path import get_render_image_filename, set_blender_output_path
from .scene_bounding_box import SceneBoundingBox

####################################################################################################
# Register and unregister
#


# ==================================================================================================
def register_classes(classes: _Iterable) -> None:
    """Register additional menu elements.

    Arguments:
        classes {_Iterable} -- tuple or list of classes to be registered in blender.
    """
    for c in classes:
        _register_class(c)
        logger.debug("Registered class: %s", c.__name__)


# ==================================================================================================
def unregister_classes(classes: _Iterable) -> None:
    """Unregister additional menu elements.

    Arguments:
        classes {_Iterable} -- tuple or list of classes to be unregistered in blender.
    """
    for c in reversed(classes):
        _unregister_class(c)
        logger.debug("Un-registered class: %s", c.__name__)

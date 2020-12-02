
import bpy

from ...utils import register_classes as _register_classes
from ...utils import unregister_classes as _unregister_classes
from .gcp_add import SFMFLOW_MT_add_gcp, view3d_mt_add_gcp

####################################################################################################
# Register and unregister
#


_CLASSES = (
    SFMFLOW_MT_add_gcp,
)


# ==================================================================================================
def menu_register() -> None:
    """Register additional menu elements."""
    _register_classes(_CLASSES)
    #
    bpy.types.VIEW3D_MT_add.prepend(view3d_mt_add_gcp)


# ==================================================================================================
def menu_unregister() -> None:
    """Unregister additional menu elements."""
    bpy.types.VIEW3D_MT_add.remove(view3d_mt_add_gcp)
    #
    _unregister_classes(_CLASSES)

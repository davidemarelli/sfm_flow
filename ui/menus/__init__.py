
import bpy

from .gcp_add import SFMFLOW_MT_add_gcp, view3d_mt_add_gcp

####################################################################################################
# Register and unregister
#


# ==================================================================================================
def menu_register() -> None:
    """Register additional menu elements."""
    bpy.utils.register_class(SFMFLOW_MT_add_gcp)
    #
    bpy.types.VIEW3D_MT_add.prepend(view3d_mt_add_gcp)


# ==================================================================================================
def menu_unregister() -> None:
    """Unregister additional menu elements."""
    bpy.types.VIEW3D_MT_add.remove(view3d_mt_add_gcp)
    #
    bpy.utils.unregister_class(SFMFLOW_MT_add_gcp)

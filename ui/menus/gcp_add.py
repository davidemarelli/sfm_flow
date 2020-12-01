
import bpy

from ...operators import (SFMFLOW_OT_add_gcp_cross1, SFMFLOW_OT_add_gcp_cross2,
                          SFMFLOW_OT_add_gcp_hourglass, SFMFLOW_OT_add_gcp_l,
                          SFMFLOW_OT_add_gcp_round1, SFMFLOW_OT_add_gcp_round2,
                          SFMFLOW_OT_add_gcp_round3, SFMFLOW_OT_add_gcp_square)

####################################################################################################
# Menu draw function
#


# ==================================================================================================
def view3d_mt_add_gcp(self, context: bpy.types.Context) -> None:   # pylint: disable=unused-argument
    """Add entries to the 3D View -> Add menu.

    Arguments:
        context {bpy.types.Context} -- draw context
    """
    self.layout.menu(SFMFLOW_MT_add_gcp.bl_idname, icon='PIVOT_CURSOR')


####################################################################################################
# Menu definition
#

class SFMFLOW_MT_add_gcp(bpy.types.Menu):
    """GCP submenu, used in 3D View -> Add."""
    bl_idname = "SFMFLOW_MT_add_gcp"
    bl_label = "GCP"

    # ==============================================================================================
    def draw(self, context: bpy.types.Context) -> None:   # pylint: disable=unused-argument
        """Add operators to the GCP submenu.

        Arguments:
            context {bpy.types.Context} -- draw context
        """
        # TODO use custom icons https://docs.blender.org/api/2.90/bpy.utils.previews.html
        layout = self.layout
        layout.operator(SFMFLOW_OT_add_gcp_cross1.bl_idname, text="Cross 1", icon='PANEL_CLOSE')
        layout.operator(SFMFLOW_OT_add_gcp_cross2.bl_idname, text="Cross 2", icon='PANEL_CLOSE')
        layout.operator(SFMFLOW_OT_add_gcp_hourglass.bl_idname, text="Hourglass", icon='DECORATE_KEYFRAME')
        layout.operator(SFMFLOW_OT_add_gcp_l.bl_idname, text="L", icon='RIGHTARROW_THIN')
        layout.operator(SFMFLOW_OT_add_gcp_round1.bl_idname, text="Round 1", icon='HANDLETYPE_AUTO_CLAMP_VEC')
        layout.operator(SFMFLOW_OT_add_gcp_round2.bl_idname, text="Round 2", icon='HANDLETYPE_AUTO_VEC')
        layout.operator(SFMFLOW_OT_add_gcp_round3.bl_idname, text="Round 3", icon='PROP_ON')
        layout.operator(SFMFLOW_OT_add_gcp_square.bl_idname, text="Square", icon='HANDLETYPE_VECTOR_VEC')

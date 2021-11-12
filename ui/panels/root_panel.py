
import bpy
from sfm_flow.operators import (SFMFLOW_OT_animate_camera, SFMFLOW_OT_animate_camera_clear,
                                SFMFLOW_OT_animate_sun, SFMFLOW_OT_animate_sun_clear,
                                SFMFLOW_OT_camera_adjust_fl_for_gsd, SFMFLOW_OT_init_scene,
                                SFMFLOW_OT_randomize_animation,
                                SFMFLOW_OT_set_average_ground_altitude)

from ..components.render_cameras import render_cameras_box


class SFMFLOW_PT_main(bpy.types.Panel):
    """SfM Flow addon main UI panel"""
    bl_idname = "SFMFLOW_PT_main"
    bl_label = "SfM Flow"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "scene"
    bl_options = {'DEFAULT_CLOSED'}
    bl_order = 0

    ################################################################################################
    # Behavior
    #

    @classmethod
    def poll(cls, context: bpy.types.Context) -> bool:
        """Panel's enabling condition.
        Show the panel only if a scene is loaded.

        Arguments:
            context {bpy.types.Context} -- poll context

        Returns:
            bool -- True to enable, False to disable
        """
        return context.scene is not None

    ################################################################################################
    # Layout
    #

    def draw(self, context):
        """Panel's layout"""
        layout = self.layout
        scene = context.scene
        properties = scene.sfmflow
        col = layout.column()
        #
        # render cameras
        render_cameras_box(col, properties)
        #
        # images path (in/out)
        row = col.split(factor=0.33)
        row.alignment = 'RIGHT'
        row.label(text="Output path")
        row.prop(properties, "output_path", text="")
        #
        # scene initialization
        layout.row().separator()
        layout.operator(SFMFLOW_OT_init_scene.bl_idname, icon='MOD_BUILD')
        #
        # average ground altitude
        row = layout.row(align=True)
        row.label(text="Ground altitude")
        row.prop(properties, "scene_ground_average_z", text="")
        row.operator(SFMFLOW_OT_set_average_ground_altitude.bl_idname, text="", icon='DRIVER_DISTANCE')
        #
        # adjust camera focal length and GSD
        layout.row().separator()
        layout.operator(SFMFLOW_OT_camera_adjust_fl_for_gsd.bl_idname)
        #
        # camera and sun animation
        r = layout.row(align=True)
        r.operator(SFMFLOW_OT_animate_camera.bl_idname, icon='ANIM')
        r.operator(SFMFLOW_OT_animate_camera_clear.bl_idname, text="", icon='X')
        r.separator_spacer()
        r.operator(SFMFLOW_OT_animate_sun.bl_idname, icon='ANIM')
        r.operator(SFMFLOW_OT_animate_sun_clear.bl_idname, text="", icon='X')
        #
        r = layout.row()
        r.operator(SFMFLOW_OT_randomize_animation.bl_idname, icon='ANIM')

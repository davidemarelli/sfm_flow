
import bpy


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
        # render camera
        row = col.split(factor=0.33)
        row.alignment = 'RIGHT'
        row.label(text="Render camera")
        row = row.split(factor=0.5, align=True)
        row.prop(scene, "camera", text="")
        row.prop(properties, "is_show_camera_pose", text="Show keyframes", toggle=True)
        #
        # images path (in/out)
        row = col.split(factor=0.33)
        row.alignment = 'RIGHT'
        row.label(text="Images path")
        row.prop(context.scene.render, "filepath", text="")
        #
        # scene initialization
        layout.row().separator()
        layout.operator("sfmflow.init_scene", icon='MOD_BUILD')
        #
        # camera and sun animation
        r = layout.row(align=True)
        r.operator("sfmflow.animate_camera", icon='ANIM')
        r.operator("sfmflow.animate_camera_clear", text="", icon='X')
        r.separator_spacer()
        r.operator("sfmflow.animate_sun", icon='ANIM')
        r.operator("sfmflow.animate_sun_clear", text="", icon='X')

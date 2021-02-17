
import bpy

from ...operators import (SFMFLOW_OT_export_cameras_gt, SFMFLOW_OT_export_gcps,
                          SFMFLOW_OT_export_ground_truth, SFMFLOW_OT_render_images)


class SFMFLOW_PT_render_tools(bpy.types.Panel):
    """SfM Flow addon, data generation and export UI panel"""
    bl_idname = "SFMFLOW_PT_render_tools"
    bl_label = "Data generation"
    bl_parent_id = "SFMFLOW_PT_main"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "scene"
    bl_options = {'DEFAULT_CLOSED'}
    bl_order = 1

    ################################################################################################
    # Layout
    #

    def draw(self, context):
        """Panel's layout"""
        layout = self.layout
        scene = context.scene
        properties = scene.sfmflow
        #
        # --- rendering effects
        col = layout.column(align=True)
        row = col.row(align=True)
        row.prop(scene.render, "use_motion_blur")
        row.prop(properties, "motion_blur_probability", text="Prob")
        row.prop(properties, "motion_blur_shutter")
        col.prop(properties, "render_with_shadows")
        #
        # --- rendering file format
        layout.separator()
        col = layout.column(align=True)
        row = col.split(factor=0.5, align=True)
        row.alignment = 'RIGHT'
        row.label(text="File format")
        row.prop(properties, "render_file_format", text="")
        #
        # --- operators
        layout.separator()
        col = layout.column()
        col.use_property_split = True
        col.use_property_decorate = False  # no animation
        col.prop(context.scene.render, "use_overwrite", text="Overwrite files")
        col.operator(SFMFLOW_OT_render_images.bl_idname, icon='RENDER_STILL')   # render dataset button
        col.operator(SFMFLOW_OT_export_ground_truth.bl_idname, icon='EXPORT')   # export geometry ground truth button
        col.operator(SFMFLOW_OT_export_gcps.bl_idname, icon='EXPORT')           # export GCPs button
        col.operator(SFMFLOW_OT_export_cameras_gt.bl_idname, icon='EXPORT')     # export cameras gt button

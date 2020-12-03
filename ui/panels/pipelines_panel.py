
import bpy

from ...operators import (SFMFLOW_OT_align_reconstruction, SFMFLOW_OT_evaluate_reconstruction,
                          SFMFLOW_OT_import_reconstruction, SFMFLOW_OT_reconstruction_filter,
                          SFMFLOW_OT_reconstruction_filter_clear, SFMFLOW_OT_run_pipelines,
                          SFMFLOW_OT_sample_geometry_gt)
from ...reconstruction import ReconstructionsManager
from ...utils import is_active_object_reconstruction


class SFMFLOW_PT_pipelines_tools(bpy.types.Panel):
    """SfM Flow addon, SfM pipelines UI panel"""
    bl_idname = "SFMFLOW_PT_pipelines_tools"
    bl_label = "Pipelines execution and evaluation"
    bl_parent_id = "SFMFLOW_PT_main"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "scene"
    bl_options = {'DEFAULT_CLOSED'}
    bl_order = 2

    ################################################################################################
    # Layout
    #

    def draw(self, context):
        """Panel's layout"""
        layout = self.layout
        scene = context.scene
        properties = scene.sfmflow
        obj = context.view_layer.objects.active
        #
        # reconstruction workspace folder
        row = layout.split(factor=0.33, align=True)
        row.label(text="Reconstruction workspace")
        row.prop(properties, "reconstruction_path", text="")
        #
        # run pipelines
        layout.row().separator()
        row = layout.split(factor=0.33, align=True)
        row.prop(properties, "reconstruction_pipeline", text="")
        row.operator(SFMFLOW_OT_run_pipelines.bl_idname, icon='SETTINGS')
        #
        # import reconstruction
        layout.row().separator()
        row = layout.row(align=True)
        row.operator(SFMFLOW_OT_import_reconstruction.bl_idname, icon='IMPORT')
        row.operator(SFMFLOW_OT_sample_geometry_gt.bl_idname, text="", icon='GROUP_VERTEX')
        #
        # reconstruction display
        row = layout.row(align=True)
        if obj:
            row.prop(obj.sfmflow, "show_recon_cameras", text="Show cameras", toggle=True)
            row.prop(obj.sfmflow, "show_recon_always", toggle=True)
        row.enabled = True if is_active_object_reconstruction(context) else False
        #
        # reconstruction filtering
        col = layout.column(align=True)
        row = col.row(align=True)
        row.operator(SFMFLOW_OT_reconstruction_filter.bl_idname, icon='FILTER')
        row.operator(SFMFLOW_OT_reconstruction_filter_clear.bl_idname, text="", icon='X')
        row = col.row(align=True)
        if context.view_layer.objects.active is not None:
            enable = False
            row.prop(context.view_layer.objects.active.sfmflow, "cloud_filtering_display_mode", expand=True)
            if is_active_object_reconstruction(context):
                model = ReconstructionsManager.get_model_by_uuid(
                    context.view_layer.objects.active['sfmflow_model_uuid'])
                if model.has_filter_model():
                    enable = True
            row.enabled = enable
        #
        # reconstruction fine alignment
        layout.operator(SFMFLOW_OT_align_reconstruction.bl_idname, icon='TRACKING_REFINE_FORWARDS')
        #
        # reconstruction evaluation
        layout.row().separator()
        layout.operator(SFMFLOW_OT_evaluate_reconstruction.bl_idname, icon='DRIVER_DISTANCE')
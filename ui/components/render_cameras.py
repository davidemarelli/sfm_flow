"""Render cameras ui components."""

import bpy

from ...operators.camera_add import SFMFLOW_OT_camera_add
from ...operators.render_cameras import (SFMFLOW_OT_RenderCameraSlotAddOperator,
                                         SFMFLOW_OT_RenderCameraSlotRemoveOperator)
from ...prefs.properties import SFMFLOW_AddonProperties, SFMFLOW_RenderCameraProperty


class RENDERCAMERA_UL_property_list_item(bpy.types.UIList):
    """UI layout for {sfm_flow.props.SFMFLOW_RenderCameraProperty}."""

    ################################################################################################
    # Item appearance
    #

    # pylint: disable=unused-argument
    def draw_item(self, context: bpy.types.Context, layout: bpy.types.UILayout,
                  data: SFMFLOW_AddonProperties, item: SFMFLOW_RenderCameraProperty, icon: int,
                  active_data: SFMFLOW_AddonProperties, active_propname: str) -> None:
        """Defines the layout of a {sfm_flow.props.SFMFLOW_RenderCameraProperty} list item."""
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            split = layout.row()
            if item.camera:
                split.label(icon='VIEW_CAMERA')
                split.label(text=item.camera.name)
            else:
                split.label(icon='CAMERA_DATA')
        elif self.layout_type in {'GRID'}:
            raise NotImplementedError("`GRID` mode is not supported for render camera list items.")


#
#
#


def render_cameras_box(layout: bpy.types.UILayout, sfmflow_properties: SFMFLOW_AddonProperties) -> None:
    """Partial template for render cameras ui box.

    Arguments:
        layout {bpy.types.UILayout} -- layout where to append the ui box
        sfmflow_properties {SFMFLOW_AddonProperties} -- properties of the addon
    """
    box = layout.box()
    row = box.row()
    row.label(text="Render cameras:")
    row.prop(sfmflow_properties, "is_show_camera_pose", text="Show keyframes", toggle=True)
    row = box.row()
    row.template_list("RENDERCAMERA_UL_property_list_item", "", sfmflow_properties,
                      "render_cameras", sfmflow_properties, "render_cameras_idx", rows=2)
    controls_col = row.column(align=True)
    controls_col.operator(SFMFLOW_OT_RenderCameraSlotAddOperator.bl_idname, text="", icon='ADD')
    controls_col.operator(SFMFLOW_OT_RenderCameraSlotRemoveOperator.bl_idname, text="", icon='REMOVE')
    #
    if sfmflow_properties.render_cameras_idx != -1:
        render_camera = sfmflow_properties.render_cameras[sfmflow_properties.render_cameras_idx]
        row = box.row(align=True)
        row.prop(render_camera, "camera", icon='CAMERA_DATA', text='')
        row.operator(SFMFLOW_OT_camera_add.bl_idname, text='New', icon='ADD')
        #
        # camera properties
        if render_camera.camera:
            box.prop(render_camera.camera.data.dof, "use_dof")

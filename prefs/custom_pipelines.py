"""Custom 3D reconstruction pipelines preferences."""

from typing import TYPE_CHECKING
from uuid import uuid1

import bpy
from bpy.props import StringProperty

if TYPE_CHECKING:   # avoid cyclic dependency
    from .preferences import AddonPreferences


class CustomPipelineProperty(bpy.types.PropertyGroup):
    """Custom reconstruction pipeline property definition."""

    uuid: StringProperty()      # unique pipeline id
    name: StringProperty()      # pipeline name
    command: StringProperty()   # pipeline command


#
#
#
#


class CustomPipelineAddOperator(bpy.types.Operator):
    """Add a custom 3D reconstruction pipeline to the add-on's preferences."""
    bl_idname = "sfmflow.prefs_add_custom_pipeline"
    bl_label = "Add custom reconstruction pipeline"

    ################################################################################################
    # Behavior
    #

    def execute(self, context: bpy.types.Context) -> set:
        """Operator execution. Add a new custom pipeline to the custom pipelines collection.

        Arguments:
            context {bpy.types.Context} -- current context

        Returns:
            set -- {'FINISHED'}
        """
        addon_user_preferences_name = (__name__)[:__name__.index('.')]
        prefs = context.preferences.addons[addon_user_preferences_name].preferences   # type: AddonPreferences

        new_cp_name = "Custom pipeline"
        new_cp_num = 0
        for cp in prefs.custom_pipelines:
            if cp.name.startswith(new_cp_name):
                new_cp_num += 1
        if new_cp_num > 0:
            new_cp_name = "{} ({})".format(new_cp_name, new_cp_num)

        custom_pipe = prefs.custom_pipelines.add()
        custom_pipe.uuid = str(uuid1())
        custom_pipe.name = new_cp_name
        custom_pipe.command = ""

        prefs.custom_pipelines_idx = len(prefs.custom_pipelines) - 1
        return {'FINISHED'}


#
#
#
#


class CustomPipelineRemoveOperator(bpy.types.Operator):
    """Remove a 3D reconstruction custom pipeline from the custom pipelines collection."""
    bl_idname = "sfmflow.prefs_remove_custom_pipeline"
    bl_label = "Remove selected custom pipeline"

    ################################################################################################
    # Behavior
    #

    # ==============================================================================================
    @classmethod
    def poll(cls, context: bpy.types.Context) -> bool:
        """Operator's enabling condition.
        The operator is enabled only if a custom 3D reconstruction is selected.

        Arguments:
            context {bpy.types.Context} -- poll context

        Returns:
            bool -- True to enable, False to disable
        """
        addon_user_preferences_name = (__name__)[:__name__.index('.')]
        prefs = context.preferences.addons[addon_user_preferences_name].preferences   # type: AddonPreferences
        return prefs.custom_pipelines_idx >= 0

    # ==============================================================================================
    def execute(self, context: bpy.types.Context) -> set:
        """Operator execution. Remove the selected custom pipeline from the collection.

        Arguments:
            context {bpy.types.Context} -- current context

        Returns:
            set -- {'FINISHED'}
        """
        addon_user_preferences_name = (__name__)[:__name__.index('.')]
        prefs = context.preferences.addons[addon_user_preferences_name].preferences   # type: AddonPreferences
        prefs.custom_pipelines.remove(prefs.custom_pipelines_idx)
        prefs.custom_pipelines_idx -= 1
        return {'FINISHED'}


#
#
#
#


class CUSTOMPIPELINE_UL_property_list_item(bpy.types.UIList):
    """UI layout for {sfm_flow.prefs.CustomPipelineProperty}."""

    ################################################################################################
    # Item appearance
    #

    # pylint: disable=unused-argument
    def draw_item(self, context: bpy.types.Context, layout: bpy.types.UILayout,
                  data: 'AddonPreferences', item: CustomPipelineProperty, icon: int,
                  active_data: 'AddonPreferences', active_propname: str) -> None:
        """Defines the layout of a {sfm_flow.prefs.CustomPipelineProperty} list item."""
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            split = layout.split(factor=0.3)
            split.label(text=item.name)
            split.label(text=item.command)
        elif self.layout_type in {'GRID'}:
            raise NotImplementedError("`GRID` mode is not supported custom pipeline list items.")

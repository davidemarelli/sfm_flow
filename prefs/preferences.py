"""SfM Flow's user preferences."""

import logging
import platform
import re
from os import path

import addon_utils
import bpy
import sfm_flow.utils.logutils as logutils
from bpy.props import (BoolProperty, CollectionProperty, EnumProperty, FloatVectorProperty,
                       IntProperty, StringProperty)
from sfm_flow.reconstruction import ReconstructionsManager
from sfm_flow.utils import register_classes as _register_classes
from sfm_flow.utils import unregister_classes as _unregister_classes

from .custom_pipelines import (CUSTOMPIPELINE_UL_property_list_item, CustomPipelineAddOperator,
                               CustomPipelineProperty, CustomPipelineRemoveOperator)

logger = logging.getLogger(__name__)


EXIFTOOL_VERSION = (11, 76)


# ==================================================================================================
def force_absolute_path(prefs: 'AddonPreferences', context: bpy.types.Context,    # pylint: disable=unused-argument
                        path_property_name: str) -> None:
    """Force to use the absolute path on string path properties.
    Call this function form the `update` callback of the properties.

    Arguments:
        prefs {AddonPreferences} -- add-on's preferences
        context {bpy.types.Context} -- current context
        path_property_name {str} -- name of the property
    """
    if prefs[path_property_name].startswith("//"):
        logger.debug("Forcing absolute path for: %s", prefs[path_property_name])
        prefs[path_property_name] = bpy.path.abspath(prefs[path_property_name])


class AddonPreferences(bpy.types.AddonPreferences):
    """Add-on's preferences definition.
    Configurable from: File -> User Preferences -> Add-ons -> SfM Flow
    """
    bl_idname = (__name__)[:__name__.index('.')]

    ################################################################################################
    # Properties
    #

    # ==============================================================================================
    # path to COLMAP installation folder
    colmap_path: StringProperty(
        name="COLMAP folder path",
        description="Path to COLMAP installation folder",
        subtype='DIR_PATH',
        update=lambda s, c: force_absolute_path(s, c, "colmap_path")
    )

    # ==============================================================================================
    # path to OpenMVG installation folder
    openmvg_path: StringProperty(
        name="OpenMVG folder path",
        description="Path to OpenMVG installation folder",
        subtype='DIR_PATH',
        update=lambda s, c: force_absolute_path(s, c, "openmvg_path")
    )

    # ==============================================================================================
    # path to OpenMVG camera sensor database
    openmvg_camera_sensor_db: StringProperty(
        name="OpenMVG camera sensor db",
        description="Path to camera sensor database for OpenMVG",
        subtype='FILE_PATH',
        default=path.abspath(path.join(path.dirname(__file__), "../assets/openmvg_camera_database.txt")),
        update=lambda s, c: force_absolute_path(s, c, "openmvg_camera_sensor_db")
    )

    # ==============================================================================================
    # path to Theia installation folder
    theia_path: StringProperty(
        name="Theia folder path",
        description="Path to Theia installation folder",
        subtype='DIR_PATH',
        update=lambda s, c: force_absolute_path(s, c, "theia_path")
    )

    # ==============================================================================================
    # path to Theia flags file template
    theia_flags_template: StringProperty(
        name="Theia flags file template",
        description="Path to flags template file for Theia."
        " Allowed tokens in the template are: {w}->ReconstructionWorkspace and {i}->ImagesFolder",
        subtype='FILE_PATH',
        default=path.abspath(path.join(path.dirname(__file__), "../assets/theia_flags_template.txt")),
        update=lambda s, c: force_absolute_path(s, c, "theia_flags_template")
    )

    # ==============================================================================================
    # path to VisualSFM installation folder
    visualsfm_path: StringProperty(
        name="VisualSFM folder path",
        description="Path to VisualSFM installation folder",
        subtype='DIR_PATH',
        update=lambda s, c: force_absolute_path(s, c, "visualsfm_path")
    )

    # ==============================================================================================
    # path to Exiftool executable OR exiftool command
    exiftool_path: StringProperty(
        name="ExifTool path",
        default="exiftool",
        description="Path to ExifTool executable",
        subtype='FILE_PATH',
        update=lambda s, c: force_absolute_path(s, c, "exiftool_path")
    )

    # ==============================================================================================
    # limit camera rendering and gt export to the last keyframe if it's before the end of the scene's end_frame
    limit_to_last_camera_keyframe: BoolProperty(
        name="Limit rendering and gt export to last camera keyframe",
        description="Limit rendering and gt export of each camera to its last animation "
        "keyframe if it occurs earlyier than the scene end frame",
        default=True
    )

    # ==============================================================================================
    # Reconstructed cameras display color
    recon_camera_color: FloatVectorProperty(
        name="Reconstructed camera color",
        description="Color used to show the reconstructed cameras in the 3D viewport",
        subtype='COLOR',
        size=3,
        min=0.0,
        max=1.0,
        default=(1., 0.25, 0.1)
    )

    # ==============================================================================================
    # Point cloud filtering display color
    filtered_points_color: FloatVectorProperty(
        name="Filtered points color",
        description="Color used to show the discarded points of a reconstructed point cloud."
        " REQUIRE restart to apply changes!",
        subtype='COLOR',
        size=3,
        min=0.0,
        max=1.0,
        default=(0., 0., 1.)
    )

    # ==============================================================================================
    # custom pipelines list
    custom_pipelines: CollectionProperty(type=CustomPipelineProperty)
    custom_pipelines_idx: IntProperty(default=-1, options={'HIDDEN', 'SKIP_SAVE'})

    # ==============================================================================================
    # addon logging level

    # ----------------------------------------------------------------------------------------------
    LOG_LEVELS = [
        (str(logutils.DISABLED), "DISABLED", "Disable logging"),
        (str(logutils.INFO), "INFO", "Log everything"),
        (str(logutils.WARNING), "WARNING", "Log only warning and errors"),
        (str(logutils.ERROR), "ERROR", "Log only errors"),
        (str(logutils.CRITICAL), "CRITICAL", "Log only critical errors"),
        (str(logutils.DEBUG), "DEBUG", "Verbose logging for debug"),
    ]

    # ----------------------------------------------------------------------------------------------
    def on_log_level_change(self, context: bpy.types.Context):   # pylint: disable=unused-argument
        """Log level change callback

        Arguments:
            context {bpy.types.Context} -- blender's context
        """
        logutils.setup_logger(log_level=int(self.log_level))

    # ----------------------------------------------------------------------------------------------
    log_level: EnumProperty(
        items=LOG_LEVELS,
        name="Log level",
        description="Minimum level for messages to be logged",
        default=str(logutils.INFO),
        update=on_log_level_change
    )

    ################################################################################################
    # Layout
    #

    def draw(self, context: bpy.types.Context):   # pylint: disable=unused-argument
        """Preference panel layout."""
        layout = self.layout
        #
        # warn user if Cycles is missing
        if addon_utils.check("cycles")[1] is False:
            row = layout.row(align=True)
            row.alert = True
            col = row.column(align=True)
            col.alignment = 'CENTER'
            col.scale_y = 1.5
            col.label(text="", icon='ERROR')
            col = row.column(align=True)
            col.scale_y = 0.75
            col.label(text="'Cycles Render Engine' is required but not enabled on your install.")
            col.label(text="Please enable it in Add-ons.")
        #
        # --- log level
        row = layout.split(factor=0.66)
        row.alignment = 'RIGHT'
        row.label(text="Log level")
        row.prop(self, "log_level", text="")
        #
        # --- log level
        row = layout.split(factor=0.66)
        row.alignment = 'RIGHT'
        row.label(text=self.rna_type.properties["limit_to_last_camera_keyframe"].name)
        row.prop(self, "limit_to_last_camera_keyframe", text="")
        #
        # --- display colors
        row = layout.split(factor=0.66)
        row.alignment = 'RIGHT'
        row.label(text="Reconstructed camera color")
        row.prop(self, "recon_camera_color", text="")   # reconstructed cameras color
        row = layout.split(factor=0.66)
        row.alignment = 'RIGHT'
        row.label(text="Filtered points color")
        row.prop(self, "filtered_points_color", text="")   # filtered points color
        #
        # --- Exiftool
        box = layout.box()
        row = box.row(align=True)
        row.alignment = 'LEFT'
        row.label(text="ExifTool:")
        et_project_page = "https://exiftool.org/"
        row.operator("wm.url_open", icon='URL', text="").url = et_project_page
        #
        os_type = platform.system()
        et_version = '.'.join(str(v) for v in EXIFTOOL_VERSION)
        if os_type == "Windows":     # windows
            row = box.row()
            row.label(text="On Windows download the executable from:")
            url = et_project_page + "exiftool-" + et_version + ".zip"
            row.operator("wm.url_open", icon='URL', text=f"ExifTool Windows Executable v{et_version}").url = url
        elif os_type == "Linux":     # linux
            box.row().label(text="On LINUX install package:   libimage-exiftool-perl")
        elif os_type == "Darwin":    # macOS
            row = box.row()
            row.label(text="On macOS download package from:")
            url = et_project_page + "ExifTool-" + et_version + ".dmg"
            row.operator("wm.url_open", icon='URL', text=f"ExifTool MacOS Package v{et_version}").url = url
        #
        row = box.split(factor=0.33)
        row.alignment = 'RIGHT'
        row.label(text="Executable")
        row.prop(self, "exiftool_path", text="")
        #
        # --- reconstruction pipelines
        box = layout.box()
        box.label(text="SfM pipelines:")
        col = box.column()
        # COLMAP folder path
        row = col.row()
        pipe = row.split(factor=0.33)
        l = pipe.row()
        l.alignment = 'RIGHT'
        l.label(text="COLMAP folder")
        pipe.prop(self, "colmap_path", text="")
        row.operator("wm.url_open", icon='URL', text="").url = "https://colmap.github.io/"
        # OpenMVG folder path
        row = col.row()
        pipe = row.split(factor=0.33)
        l = pipe.row()
        l.alignment = 'RIGHT'
        l.label(text="OpenMVG folder")
        pipe.prop(self, "openmvg_path", text="")
        row.operator("wm.url_open", icon='URL', text="").url = "https://github.com/openMVG/openMVG"
        # OpenMVG camera sensor database
        row = col.row()
        pipe = row.split(factor=0.33)
        l = pipe.row()
        l.alignment = 'RIGHT'
        l.label(text="OpenMVG camera db")
        pipe.prop(self, "openmvg_camera_sensor_db", text="")
        row.operator("wm.url_open", icon='URL', text="").url = "https://github.com/openMVG/openMVG/blob/develop/src/" \
            "openMVG/exif/sensor_width_database/" \
            "sensor_width_camera_database.txt"
        # Theia folder path
        row = col.row()
        pipe = row.split(factor=0.33)
        l = pipe.row()
        l.alignment = 'RIGHT'
        l.label(text="Theia folder")
        pipe.prop(self, "theia_path", text="")
        row.operator("wm.url_open", icon='URL', text="").url = "http://theia-sfm.org/"
        # Theia flags file template
        row = col.row()
        pipe = row.split(factor=0.33)
        l = pipe.row()
        l.alignment = 'RIGHT'
        l.label(text="Theia flags template")
        pipe.prop(self, "theia_flags_template", text="")
        row.operator("wm.url_open", icon='URL', text="").url = "https://github.com/sweeneychris/TheiaSfM/" \
            "blob/master/applications/build_reconstruction_flags.txt"
        # VisualSFM folder path
        row = col.row()
        pipe = row.split(factor=0.33)
        l = pipe.row()
        l.alignment = 'RIGHT'
        l.label(text="VisualSFM folder")
        pipe.prop(self, "visualsfm_path", text="")
        row.operator("wm.url_open", icon='URL', text="").url = "http://ccwu.me/vsfm/"
        #
        # --- custom reconstruction pipelines
        box = layout.box()
        box.label(text="Custom SfM pipelines:")
        row = box.row()
        row.template_list("CUSTOMPIPELINE_UL_property_list_item", "", self,
                          "custom_pipelines", self, "custom_pipelines_idx", rows=2)
        controls_col = row.column(align=True)
        controls_col.operator(CustomPipelineAddOperator.bl_idname, text="", icon='ADD')
        controls_col.operator(CustomPipelineRemoveOperator.bl_idname, text="", icon='REMOVE')
        #
        if self.custom_pipelines_idx != -1:
            col = box.column()
            row = col.split(factor=0.33)
            row.alignment = 'RIGHT'
            row.label(text="Pipeline name")
            row.prop(self.custom_pipelines[self.custom_pipelines_idx], "name", text="")
            row = col.split(factor=0.33)
            row.alignment = 'RIGHT'
            row.label(text="Pipeline command")
            row.prop(self.custom_pipelines[self.custom_pipelines_idx], "command", text="")
            #
            row = col.split(factor=0.5)
            row.label(text="Available tokens for pipeline command:")
            col = row.column(align=True)
            row = col.split(factor=0.25, align=True)
            row.label(text="{i}")
            row.label(text="images folder")
            row = col.split(factor=0.25, align=True)
            row.label(text="{w}")
            row.label(text="reconstruction workspace")

    ################################################################################################
    # Backup and restore
    #

    # ==============================================================================================
    def backup(self) -> None:
        """Backup current preferences to a temporary dictionary.
        This is used for development purpose to avoid property reset on add-on reload.
        @see also restore()
        """
        bpy.types.Scene.sfmflow_preferences_backup = {}
        pattern = re.compile(r"^([A-Z]+|bl_|rna_|__|custom_pipelines)")
        for a in dir(self):
            val = getattr(self, a)
            if not callable(val) and not pattern.match(a):
                bpy.types.Scene.sfmflow_preferences_backup.update({a: val})
        logger.debug("User preferences temporary saved to 'bpy.types.Scene.sfmflow_preferences_backup'")

    # ==============================================================================================
    def restore(self) -> None:
        """Restore preferences from a temporary dictionary (if exists).
        This is used for development purpose to avoid property reset on add-on reload.
        @see also backup()
        """
        if hasattr(bpy.types.Scene, "sfmflow_preferences_backup"):
            back_prefs = bpy.types.Scene.sfmflow_preferences_backup
            for key, value in back_prefs.items():
                if hasattr(self, key):
                    setattr(self, key, value)
            del bpy.types.Scene.sfmflow_preferences_backup  # remove temporary backup
            logger.debug("User preferences restored from 'bpy.types.Scene.sfmflow_preferences_backup'")


#
#
#
#


####################################################################################################
# Register and unregister
#

_CLASSES = (
    CUSTOMPIPELINE_UL_property_list_item,
    CustomPipelineProperty,
    CustomPipelineAddOperator,
    CustomPipelineRemoveOperator,
    AddonPreferences,
)


# ==================================================================================================
def preferences_register() -> None:
    """Register user's preferences."""
    _register_classes(_CLASSES)
    #
    addon_user_preferences_name = (__name__)[:__name__.index('.')]
    prefs = bpy.context.preferences.addons[addon_user_preferences_name].preferences   # type: AddonPreferences
    prefs.restore()   # try to restore preferences from temporary backup
    ReconstructionsManager.restore()   # try to restore existing reconstructions


# ==================================================================================================
def preferences_unregister() -> None:
    """Unregister user's preferences."""
    ReconstructionsManager.backup()   # temporary backup existing reconstructions
    addon_user_preferences_name = (__name__)[:__name__.index('.')]
    prefs = bpy.context.preferences.addons[addon_user_preferences_name].preferences   # type: AddonPreferences
    prefs.backup()   # temporary backup current preferences
    #
    _unregister_classes(_CLASSES)


from typing import List, Tuple

import bpy

from ..utils import get_objs


class SFMFLOW_AddonProperties(bpy.types.PropertyGroup):
    """Add-on's scene data type definition."""

    ################################################################################################
    # Properties
    #

    # ==============================================================================================
    # path to reconstruction folder
    reconstruction_path: bpy.props.StringProperty(
        name="Reconstruction workspace",
        default="//reconstructions/",
        description="Path to the 3D reconstruction workspace",
        subtype='DIR_PATH',
    )

    # ==============================================================================================
    # display camera poses flag
    is_show_camera_pose: bpy.props.BoolProperty(
        name="Show camera poses",
        description="Show camera keyframes positions (only when render camera is selected)",
        default=True
    )

    # ==============================================================================================
    # render with shadows

    def toggle_shadows_callback(self, context: bpy.types.Context) -> None:
        """Callback on shadow casting checkbox toggling.

        Arguments:
            context {bpy.types.Context} -- current context
        """
        objs = get_objs(context.scene)
        for obj in objs:
            obj.cycles_visibility.shadow = self.render_with_shadows

    render_with_shadows: bpy.props.BoolProperty(
        name="Shadows",
        description="Render images with shadows",
        default=True,  # changed at .blend load time, @see set_defaults
        update=toggle_shadows_callback,
        options={'SKIP_SAVE'}
    )

    # ==============================================================================================
    # motion blur probability in rendered images
    motion_blur_probability: bpy.props.FloatProperty(
        name="Motion blur probability",
        description="Percentage of frames that will have motion blur",
        subtype='PERCENTAGE',
        default=33.333,
        precision=0,
        min=0.0,
        max=100.0
    )

    # ==============================================================================================
    # motion blur shutter time
    motion_blur_shutter: bpy.props.FloatProperty(
        # this property is similar to `scene.render.motion_blur_shutter` but the usage is
        # different. The latter is animated to enable/disable the blur for each frame,
        # the first one is the constant desired shutter value for the frame with blur.
        name="Shutter",
        description="Time taken in frames between shutter open and close",
        default=0.15,
        min=0.0
    )

    # ==============================================================================================
    # flag for scene initialization, when {True} prevents scene re-initialization
    is_scene_init: bpy.props.BoolProperty(default=False)

    # ==============================================================================================
    # select 3D reconstruction pipeline to run
    def get_custom_pipelines(self, context: bpy.context) -> List[Tuple[str, str, str]]:
        """Get the list of available reconstruction pipelines.

        Arguments:
            context {bpy.context} -- current context

        Returns:
            List[Tuple[str, str, str]] -- List of {EnumProperty} items
        """
        addon_user_preferences_name = (__name__)[:__name__.index('.')]
        prefs = context.preferences.addons[addon_user_preferences_name].preferences  # type: AddonPreferences
        items = []
        #
        # default pipelines
        if prefs.colmap_path:
            items.append(("colmap", "COLMAP",
                          "General-purpose Structure-from-Motion (SfM) and Multi-View Stereo (MVS) pipeline"))
        if prefs.openmvg_path:
            items.append((("openmvg", "OpenMVG", "Open Multiple View Geometry library")))
        if prefs.theia_path:
            items.append(("theia", "Theia",
                          "Library providing efficient and reliable algorithms for Structure from Motion (SfM)"))
        if prefs.visualsfm_path:
            items.append(("visualsfm", "VisualSFM",
                          "GUI application for 3D reconstruction using structure from motion (SfM)"))
        #
        # custom pipelines
        for cp in prefs.custom_pipelines:
            items.append((cp.uuid, cp.name, cp.command))
        #
        items.sort(key=lambda t: t[1])   # sort by name
        return items

    reconstruction_pipeline: bpy.props.EnumProperty(
        name="Reconstruction pipelines",
        description="Available 3D reconstruction pipelines",
        items=get_custom_pipelines,
        options={'SKIP_SAVE'}
    )

    ################################################################################################
    # Methods
    #

    # ==============================================================================================
    def set_defaults(self) -> None:
        """Set default values for properties that require complex setup."""
        # render_with_shadows is true only if shadows are enabled for all objects
        self.render_with_shadows = all(item.cycles_visibility.shadow is True for item in get_objs(bpy.context.scene))

    ################################################################################################
    # Register and unregister
    #

    # ==============================================================================================
    @classmethod
    def register(cls):
        """Register add-on's properties."""
        bpy.types.Scene.sfmflow = bpy.props.PointerProperty(type=cls)

    # ==============================================================================================
    @classmethod
    def unregister(cls):
        """Unregister add-on's properties."""
        del bpy.types.Scene.sfmflow

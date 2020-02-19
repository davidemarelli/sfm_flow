
import bpy

from .manager import ReconstructionsManager


class SFMFLOW_ReconstructionModelProperties(bpy.types.PropertyGroup):
    """Reconstruction properties definition."""

    ################################################################################################
    # Properties
    #

    # ==============================================================================================
    # reconstruction filtering display mode

    def update_reconstruction_show(self, context: bpy.context) -> None:
        """Callback on `cloud_filtering_display_mode` changes.
        On such event update the currently selected reconstruction view mode in the viewport.

        Arguments:
            context {bpy.context} -- current context
        """
        model = ReconstructionsManager.get_model_by_uuid(context.view_layer.objects.active['sfmflow_model_uuid'])
        model.show()   # update model rendering in viewport

    cloud_filtering_display_mode: bpy.props.EnumProperty(
        name="Cloud filtering",
        description="Display mode for point cloud filtering",
        items=[
            ("cloud_filter.all", "All", "Show all the points"),
            ("cloud_filter.color", "Color filter", "Show discarded points in a different color"),
            ("cloud_filter.filtered", "Only filtered", "Show only filtered points"),
        ],
        default="cloud_filter.color",
        update=update_reconstruction_show
    )

    # ==============================================================================================
    # flag to enable display of reconstructed cameras
    show_recon_cameras: bpy.props.BoolProperty(
        name="Show reconstructed cameras",
        description="Show the reconstructed camera poses",
        default=True
    )

    # ==============================================================================================
    # flag to disable depth test while rendering reconstruction (shows occluded vertices)
    show_recon_always: bpy.props.BoolProperty(
        name="Show hidden points",
        description="Show parts of the reconstruction that are occluded",
        default=False
    )

    ################################################################################################
    # Register and unregister
    #

    # ==============================================================================================
    @classmethod
    def register(cls):
        """Register add-on's object properties"""
        bpy.types.Object.sfmflow = bpy.props.PointerProperty(type=cls)

    # ==============================================================================================
    @classmethod
    def unregister(cls):
        """Un-register add-on's object properties"""
        del bpy.types.Object.sfmflow

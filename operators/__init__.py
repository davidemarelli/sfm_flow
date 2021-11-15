
from sfm_flow.utils import register_classes as _register_classes
from sfm_flow.utils import unregister_classes as _unregister_classes

from .add_gcp import SFMFLOW_OT_add_gcp_square  # SFMFLOW_OT_add_gcp_l,
from .add_gcp import (SFMFLOW_OT_add_gcp_cross1, SFMFLOW_OT_add_gcp_cross2,
                      SFMFLOW_OT_add_gcp_hourglass, SFMFLOW_OT_add_gcp_round1,
                      SFMFLOW_OT_add_gcp_round2, SFMFLOW_OT_add_gcp_round3)
from .align_reconstruction import SFMFLOW_OT_align_reconstruction
from .animate_camera import SFMFLOW_OT_animate_camera, SFMFLOW_OT_animate_camera_clear
from .animate_sun import SFMFLOW_OT_animate_sun, SFMFLOW_OT_animate_sun_clear
from .camera_add import SFMFLOW_OT_camera_add
from .camera_adjust_fl_for_gsd import SFMFLOW_OT_camera_adjust_fl_for_gsd
from .evaluate_reconstruction import SFMFLOW_OT_evaluate_reconstruction
from .export_cameras_gt import SFMFLOW_OT_export_cameras_gt
from .export_gcps import SFMFLOW_OT_export_gcps
from .export_ground_truth import SFMFLOW_OT_export_ground_truth
from .filter_reconstruction import (SFMFLOW_OT_reconstruction_filter,
                                    SFMFLOW_OT_reconstruction_filter_clear)
from .import_reconstruction import SFMFLOW_OT_import_reconstruction
from .init_scene import SFMFLOW_OT_init_scene
from .randomize_animation import SFMFLOW_OT_randomize_animation
from .render import SFMFLOW_OT_render_images
from .render_cameras import SFMFLOW_OT_render_camera_slot_add, SFMFLOW_OT_render_camera_slot_remove
from .run_pipelines import SFMFLOW_OT_run_pipelines
from .sample_geometry_gt import SFMFLOW_OT_sample_geometry_gt
from .set_average_ground_altitude import SFMFLOW_OT_set_average_ground_altitude

####################################################################################################
# Register and unregister
#

_CLASSES = (
    SFMFLOW_OT_init_scene,
    SFMFLOW_OT_animate_camera,
    SFMFLOW_OT_animate_camera_clear,
    SFMFLOW_OT_render_images,
    SFMFLOW_OT_export_ground_truth,
    SFMFLOW_OT_evaluate_reconstruction,
    SFMFLOW_OT_reconstruction_filter,
    SFMFLOW_OT_reconstruction_filter_clear,
    SFMFLOW_OT_animate_sun,
    SFMFLOW_OT_animate_sun_clear,
    SFMFLOW_OT_run_pipelines,
    SFMFLOW_OT_import_reconstruction,
    SFMFLOW_OT_sample_geometry_gt,
    SFMFLOW_OT_align_reconstruction,
    SFMFLOW_OT_add_gcp_cross1,
    SFMFLOW_OT_add_gcp_cross2,
    SFMFLOW_OT_add_gcp_hourglass,
    # SFMFLOW_OT_add_gcp_l,
    SFMFLOW_OT_add_gcp_round1,
    SFMFLOW_OT_add_gcp_round2,
    SFMFLOW_OT_add_gcp_round3,
    SFMFLOW_OT_add_gcp_square,
    SFMFLOW_OT_export_gcps,
    SFMFLOW_OT_camera_add,
    SFMFLOW_OT_render_camera_slot_add,
    SFMFLOW_OT_render_camera_slot_remove,
    SFMFLOW_OT_export_cameras_gt,
    SFMFLOW_OT_set_average_ground_altitude,
    SFMFLOW_OT_camera_adjust_fl_for_gsd,
    SFMFLOW_OT_randomize_animation,
)


# ==================================================================================================
def operators_register() -> None:
    """Register additional functionalities."""
    _register_classes(_CLASSES)


# ==================================================================================================
def operators_unregister() -> None:
    """Unregister additional functionalities."""
    _unregister_classes(_CLASSES)

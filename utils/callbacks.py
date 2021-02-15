
# import atexit
import logging
import os
import sys
import tempfile

import bpy
from bpy.app.handlers import persistent
from sfm_flow.reconstruction import ReconstructionsManager
from sfm_flow.utils.camera import is_active_object_camera
from sfm_flow.utils.object import hide_motion_path, show_motion_path

from . import GroundTruthWriter

logger = logging.getLogger(__name__)


class Callbacks:
    """This 'static' class is used to define static callbacks handler and the relative data."""

    ################################################################################################
    # Camera motion path updates
    #

    _is_cam_pose_updating = False  # flag to avoid multiple callback calls
    _last_active_camera = None     # last active camera with motion path

    @staticmethod
    @persistent
    def cam_pose_update(scene: bpy.types.Scene) -> None:
        """Callback for the update of camera motion path on scene changes.
        Motion path is shown if scene's camera is selected and animation length is > 1.
        This callback is meant to be used on event `bpy.app.handlers.depsgraph_update_post`.

        Arguments:
            scene {bpy.types.Scene} -- blender's scene
        """
        if not Callbacks._is_cam_pose_updating:
            Callbacks._is_cam_pose_updating = True
            if scene.sfmflow.is_show_camera_pose and is_active_object_camera(bpy.context):
                camera = bpy.context.active_object
                if Callbacks._last_active_camera and (camera is not Callbacks._last_active_camera):
                    hide_motion_path(Callbacks._last_active_camera)
                Callbacks._last_active_camera = camera
                show_motion_path(camera, scene)
            elif Callbacks._last_active_camera and Callbacks._last_active_camera.motion_path:
                hide_motion_path(Callbacks._last_active_camera)
                Callbacks._last_active_camera = None
            #
            Callbacks._is_cam_pose_updating = False

    ################################################################################################
    # Post .blend save update
    #

    @staticmethod
    @persistent
    def post_save(dummy) -> None:  # pylint: disable=unused-argument
        """Post save actions handling.
        1. Adjust data generation path.
        """
        # set render output folder to a default value if not yet configured
        context = bpy.context
        if context.preferences.filepaths.temporary_directory == '':
            temp_dir = tempfile.gettempdir()
        else:
            temp_dir = context.preferences.filepaths.temporary_directory
        if os.path.realpath(context.scene.render.filepath) == temp_dir:
            projectName = bpy.path.clean_name(
                bpy.path.display_name_from_filepath(bpy.path.basename(bpy.data.filepath)))
            context.scene.render.filepath = "//" + projectName + "-render/"  # render output path

    ################################################################################################
    # Post .blend load update
    #

    @staticmethod
    @persistent
    def post_load(dummy) -> None:  # pylint: disable=unused-argument
        """Post load actions handling (bpy.app.handlers.load_post).
        1. Start rendering if required.
        2. Export ground truth csv file if required.
        """
        ReconstructionsManager.remove_all()
        #
        #
        logger.debug("sys.argv: %s", sys.argv)
        if bpy.data.is_saved:   # avoid running the commands when the default startup file is loaded
            # when blender is started at first is loaded the startup file then the correct .blend file.
            # if no checks are performed and the flags are present the requested operations will be
            # executed on the startup file!
            scene = bpy.context.scene
            scene.sfmflow.set_defaults()
            #
            # start rendering
            if "--sfmflow_render" in sys.argv:
                logger.info("Found `--sfmflow_render` flag. Starting rendering...")
                bpy.ops.sfmflow.render_images('EXEC_DEFAULT')
            #
            # export ground truth csv files
            if "--export_csv" in sys.argv:
                logger.info("Found `--export_csv` flag. Exporting CSV file...")
                i = sys.argv.index("--export_csv") + 1
                if len(sys.argv) > i and (os.path.dirname(sys.argv[i]) != ''):
                    folder_path = sys.argv[i]
                else:
                    logger.error("A file path must be specified after `--export_csv`")
                    return {'CANCELLED'}
                gt_writer = GroundTruthWriter(scene, scene.camera, folder_path, overwrite=True)
                gt_writer.save_entry_for_all_frames()


####################################################################################################
# On Blender exit
#

# @atexit.register
# def goodbye() -> None:
#     """On Blender exit release resources to avoid mem-leak/errors."""
#     # currently there is no callback on blender exit so i'm using atexit but this does not
#     # guarantee that all the blender's data is still valid.
#     #
#     # TODO find a way to correctly release draw handlers in reconstruction models
#     # the following lines causes segmentation faults (apparently only when not in debug mode)
#     logger.debug("Release resources and prepare for exit")
#     ReconstructionsManager.free()

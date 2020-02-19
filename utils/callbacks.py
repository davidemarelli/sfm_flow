
# import atexit
import logging
import os
import sys
import tempfile

import bpy
from bpy.app.handlers import persistent
from mathutils import Vector
from sfm_flow.reconstruction import ReconstructionsManager

from . import GroundTruthWriter

logger = logging.getLogger(__name__)


class Callbacks:
    """This 'static' class is used to define static callbacks handler and the relative data."""

    ################################################################################################
    # Camera motion path updates
    #

    _is_cam_pose_updating = False  # Flag to avoid multiple callback calls

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
            if scene.camera:
                show = False
                #
                # check visibility
                sel_objs = bpy.context.selected_objects
                if scene.sfmflow.is_show_camera_pose and scene.frame_start != scene.frame_end:
                    for o in sel_objs:
                        if o is scene.camera:
                            # camera is selected and makes sense to show the motion path
                            show = True
                #
                # show/hide path
                if show:
                    bpy.ops.object.select_all(action='DESELECT')
                    scene.camera.select_set(True)
                    if not scene.camera.motion_path:
                        bpy.ops.object.paths_calculate(start_frame=scene.frame_start, end_frame=scene.frame_end)
                        motion_path = scene.camera.motion_path
                        motion_path.lines = False
                        motion_path.color = Vector((1, 0, 0))  # Red
                        motion_path.use_custom_color = True
                        motion_path_viz = scene.camera.animation_visualization.motion_path
                        motion_path_viz.show_keyframe_numbers = False
                        motion_path_viz.show_keyframe_highlight = False
                    else:
                        bpy.ops.object.paths_update()
                elif scene.camera.motion_path:
                    bpy.ops.object.select_all(action='DESELECT')
                    scene.camera.select_set(True)
                    bpy.ops.object.paths_clear(only_selected=True)
                #
                # restore selection
                bpy.ops.object.select_all(action='DESELECT')
                list(map(lambda o: o.select_set(True), sel_objs))
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

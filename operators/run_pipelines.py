
import logging
import os
import platform
import shlex
import subprocess
from multiprocessing import cpu_count
from typing import Dict, List

import bpy

from ..prefs import AddonPreferences
from .threaded_operator import ThreadedOperator

logger = logging.getLogger(__name__)


class SFMFLOW_OT_run_pipelines(ThreadedOperator):
    "Run 3D reconstruction pipelines"
    bl_idname = "sfmflow.run_pipelines"
    bl_label = "Run 3D reconstruction"
    bl_options = {'REGISTER'}

    ################################################################################################
    # Behavior
    #

    # ==============================================================================================
    def invoke(self, context: bpy.types.Context, event: bpy.types.Event) -> set:  # pylint: disable=unused-argument
        """Set data before execution.

        Arguments:
            context {bpy.types.Context} -- invoke context
            event {bpy.types.Event} -- invoke event

        Returns:
            set -- enum set in {‘RUNNING_MODAL’, ‘CANCELLED’, ‘FINISHED’, ‘PASS_THROUGH’, ‘INTERFACE’}
        """
        properties = context.scene.sfmflow
        recon_ws_folder = properties.reconstruction_path
        pipeline_name = properties.reconstruction_pipeline
        # set arguments for thread
        self.heavy_load_args = (pipeline_name,
                                bpy.path.abspath(context.scene.render.filepath),
                                bpy.path.abspath(recon_ws_folder))
        return self.execute(context)

    # ==============================================================================================
    def heavy_load(self, pipeline_name: str, images_folder: str, reconstructions_folder: str, **kwargs: Dict) -> None:   # pylint: disable=arguments-differ
        """Run n 3D reconstruction pipeline.

        Arguments:
            pipeline_name {str} -- name of the pipeline, one of {'colmap', 'openmvg', 'theia', 'visualsfm'}
            images_folder {str} -- path to the folder containing the images
            reconstructions_folder {str} -- path to the reconstruction workspace
            kwargs {Dict} -- additional keyword args, unused
        """
        logger.info("Starting execution of pipeline '%s' with images in folder: %s", pipeline_name, images_folder)
        #
        user_preferences = bpy.context.preferences
        addon_user_preferences_name = (__name__)[:__name__.index('.')]
        addon_prefs = user_preferences.addons[addon_user_preferences_name].preferences  # type: AddonPreferences
        #
        if pipeline_name == "colmap":
            colmap_ws = os.path.join(reconstructions_folder, "COLMAP")
            os.makedirs(colmap_ws, exist_ok=True)
            self.run_colmap(addon_prefs.colmap_path, images_folder, colmap_ws)
        elif pipeline_name == "openmvg":
            openmvg_ws = os.path.join(reconstructions_folder, "OpenMVG")
            os.makedirs(openmvg_ws, exist_ok=True)
            self.run_openmvg(addon_prefs.openmvg_path, addon_prefs.openmvg_camera_sensor_db, images_folder, openmvg_ws)
        elif pipeline_name == "theia":
            theia_ws = os.path.join(reconstructions_folder, "Theia")
            os.makedirs(theia_ws, exist_ok=True)
            self.run_theia(addon_prefs.theia_path, images_folder, theia_ws)
        elif pipeline_name == "visualsfm":
            visualsfm_ws = os.path.join(reconstructions_folder, "VisualSFM")
            os.makedirs(visualsfm_ws, exist_ok=True)
            self.run_visualsfm(addon_prefs.visualsfm_path, images_folder, visualsfm_ws)
        else:
            # check if is a custom pipeline
            cp = next((e for e in addon_prefs.custom_pipelines if e.uuid == pipeline_name), None)
            if cp is not None:
                cp_ws = os.path.join(reconstructions_folder, "".join([c if c.isalnum() else "_" for c in cp.name]))
                os.makedirs(cp_ws, exist_ok=True)
                command = shlex.split(cp.command)   # split command and args
                command = [replace_tokens(c, images_folder, cp_ws) for c in command]
                logfile_path = os.path.join(cp_ws, bpy.path.clean_name(cp.name) + "_execution.log")
                self.run_commands(cp.name, [command, ], logfile_path)
            else:
                msg = "Unknown SfM pipeline '{}'!".format(pipeline_name)
                logger.error(msg)
                self.report({'ERROR'}, msg)
        #
        logger.info("Execution of pipeline '%s' ended, reconstruction folder: %s",
                    pipeline_name, reconstructions_folder)

    ################################################################################################
    # Execution helpers
    #

    # ==============================================================================================
    def run_colmap(self, pipeline_path: str, images_folder: str, workspace: str, save_log: bool = True) -> None:
        """Run the COLMAP 3D reconstruction SfM pipeline.

        Arguments:
            pipeline_path {str} -- path to the pipeline installation folder
            images_folder {str} -- path to the folder containing the images
            workspace {str} -- path to the reconstruction workspace

        Keyword Arguments:
            save_log {bool} -- if {True} the reconstruction log is saved to file `colmap_execution.log`
                               in the reconstruction workspace (default: {True})
        """
        if platform.system() == "Windows":
            pipeline_path = os.path.join(pipeline_path, "COLMAP.bat")
        elif os.path.isdir(pipeline_path):
            pipeline_path = os.path.join(pipeline_path, "colmap")
        db_path = os.path.join(workspace, "database.db")
        #
        commands = [
            [pipeline_path, "feature_extractor",
             "--database_path", db_path,
             "--image_path", images_folder],
            [pipeline_path, "exhaustive_matcher", "--database_path", db_path],
            [pipeline_path, "mapper",
             "--database_path", db_path,
             "--image_path", images_folder,
             "--output_path", workspace],
            [pipeline_path, "model_converter",
             "--input_path", os.path.join(workspace, '0'),
             "--output_path", os.path.join(workspace, 'reconstruction.nvm'),
             "--output_type", 'NVM']
        ]
        #
        logfile_path = os.path.join(workspace, "colmap_execution.log") if save_log else None
        self.run_commands("COLMAP", commands, logfile_path)

    # ==============================================================================================
    def run_openmvg(self, pipeline_path: str, camera_db_filepath: str, images_folder: str,
                    workspace: str, save_log: bool = True) -> None:
        """Run the OpenMVG 3D reconstruction SfM pipeline.

        Arguments:
            pipeline_path {str} -- path to the pipeline installation folder
            images_folder {str} -- path to the folder containing the images
            workspace {str} -- path to the reconstruction workspace

        Keyword Arguments:
            save_log {bool} -- if {True} the reconstruction log is saved to file `openmvg_execution.log`
                               in the reconstruction workspace (default: {True})
        """
        matches_dir = os.path.join(workspace, "matches")
        reconstruction_dir = os.path.join(workspace, "reconstruction_sequential")
        out_dir = os.path.join(workspace, "output")
        cores = str(cpu_count())
        #
        commands = [
            [os.path.join(pipeline_path, "openMVG_main_SfMInit_ImageListing"), "-i",
             images_folder, "-o", matches_dir, "-d", camera_db_filepath],
            [os.path.join(pipeline_path, "openMVG_main_ComputeFeatures"), "-i", matches_dir +
             "/sfm_data.json", "-o", matches_dir, "-m", "SIFT", "-n", cores],
            [os.path.join(pipeline_path, "openMVG_main_ComputeMatches"), "-i",
             matches_dir+"/sfm_data.json", "-o", matches_dir],
            [os.path.join(pipeline_path, "openMVG_main_IncrementalSfM"), "-i", matches_dir +
             "/sfm_data.json", "-m", matches_dir, "-o", reconstruction_dir],
            [os.path.join(pipeline_path, "openMVG_main_ComputeSfM_DataColor"), "-i", reconstruction_dir +
             "/sfm_data.bin", "-o", os.path.join(reconstruction_dir, "colorized.ply")],
            # openMVG_main_openMVG2NVM renames the images making impossible to recover the camera
            # reconstruction <--> gt correspondence.
            [os.path.join(pipeline_path, "openMVG_main_openMVG2PMVS"), "-i",
             reconstruction_dir + "/sfm_data.bin", "-o", out_dir, "-c", cores]
        ]
        #
        logfile_path = os.path.join(workspace, "openmvg_execution.log") if save_log else None
        self.run_commands("OpenMVG", commands, logfile_path)

    # ==============================================================================================
    def run_theia(self, pipeline_path: str, images_folder: str, workspace: str, save_log: bool = True) -> None:
        """Run the Theia 3D reconstruction SfM pipeline.

        Arguments:
            pipeline_path {str} -- path to the pipeline installation folder
            images_folder {str} -- path to the folder containing the images
            workspace {str} -- path to the reconstruction workspace

        Keyword Arguments:
            save_log {bool} -- if {True} the reconstruction log is saved to file `theia_execution.log`
                               in the reconstruction workspace (default: {True})
        """
        flags_file_path = write_theia_flags_file(images_folder, workspace)
        #
        commands = [
            [os.path.join(pipeline_path, "build_reconstruction"), "--flagfile", flags_file_path],
            [os.path.join(pipeline_path, "colorize_reconstruction"), "--flagfile", flags_file_path],
            [os.path.join(pipeline_path, "export_to_nvm_file"), "--flagfile", flags_file_path]
        ]
        #
        logfile_path = os.path.join(workspace, "theia_execution.log") if save_log else None
        self.run_commands("Theia", commands, logfile_path)

    # ==============================================================================================
    def run_visualsfm(self, pipeline_path: str, images_folder: str, workspace: str, save_log: bool = True) -> None:
        """Run the VisualSFM 3D reconstruction SfM pipeline.

        Arguments:
            pipeline_path {str} -- path to the pipeline installation folder
            images_folder {str} -- path to the folder containing the images
            workspace {str} -- path to the reconstruction workspace

        Keyword Arguments:
            save_log {bool} -- if {True} the reconstruction log is saved to file `visualsfm_execution.log`
                               in the reconstruction workspace (default: {True})
        """
        recon_nvm_file = os.path.join(workspace, "reconstruction.nvm")
        #
        commands = [
            [os.path.join(pipeline_path, "VisualSFM"), "sfm",
             images_folder, recon_nvm_file]
        ]
        #
        logfile_path = os.path.join(workspace, "visualsfm_execution.log") if save_log else None
        self.run_commands("VisualSFM", commands, logfile_path)

    # ==============================================================================================
    def run_commands(self, pipeline_name: str, commands: List[str], logfile_path: str = None) -> None:
        """Run al list of external commands, report progress through blender's UI.

        Arguments:
            pipeline_name {str} -- name of the pipeline/program in execution
            commands {List[str]} -- list of commands to be executed

        Keyword Arguments:
            logfile_path {str} -- command logfile (default: {None})
        """
        logfile = None
        if logfile_path:
            logfile = open(logfile_path, "w")
        #
        try:
            phase_number = 0
            for command in commands:
                if logfile:
                    logfile.write("\n\n@@@ Log for command: %s\n\n" % command)
                phase_number += 1
                self.progress_string = "Running {}... (step {} of {})".format(
                    pipeline_name, phase_number, len(commands))
                process = subprocess.run(command, stdout=logfile, stderr=logfile, universal_newlines=True, check=True)
            #
            # execution of all commands completed correctly
            msg = "{} completed correctly".format(pipeline_name)
            self.progress_string = msg
            self.exit_code = process.returncode
            logger.info(msg)
        #
        except Exception as e:   # pylint: disable=broad-except
            msg = "{} exited with errors! (error: {})".format(pipeline_name, e)
            self.progress_string = None
            self.exit_code = -1
            logger.error(msg)
        finally:
            if logfile:
                logfile.close()


#
#
#
#

# ===================================================================================================
def replace_tokens(command: str, images_folder: str, reconstruction_folder: str) -> str:
    """Replace tokens in a command string.

    Arguments:
        command {str} -- command string
        images_folder {str} -- path to the folder contining the images
        reconstruction_folder {str} -- path to the reconstruction folder

    Returns:
        str -- updated command string
    """
    return command.replace("{i}", images_folder).replace("{w}", reconstruction_folder)


# ===================================================================================================
def write_theia_flags_file(images_folder: str, reconstruction_folder: str) -> str:
    """Write a Theia reconstruction flag file.
    The file is generated by replacing the tokens in a given template file with the actual values.

    Arguments:
        images_folder {str} -- path to the folder contining the images
        reconstruction_folder {str} -- path to the reconstruction folder

    Returns:
        str -- path to the flag file
    """
    # get theia template path
    addon_prefs_name = (__name__)[:__name__.index('.')]
    flags_template_filepath = bpy.context.preferences.addons[addon_prefs_name].preferences.theia_flags_template
    #
    # write flags file replacing tokens
    flags_filepath = os.path.join(reconstruction_folder, "flags.txt")
    with open(flags_template_filepath, 'r') as t, open(flags_filepath, 'w') as f:
        for line in t:
            f.write(replace_tokens(line, images_folder, reconstruction_folder))
    return flags_filepath


import logging
import os
import sys
from math import floor, sqrt
from subprocess import CalledProcessError, TimeoutExpired, check_output, run

import bpy
from bpy.app.handlers import persistent

from ..utils import GroundTruthWriter
from ..utils.animation import animate_motion_blur

logger = logging.getLogger(__name__)


class SFMFLOW_OT_render_images(bpy.types.Operator):
    """Render dataset images, sets EXIF metadata and save camera poses file"""
    bl_idname = "sfmflow.render_images"
    bl_label = "Render dataset"

    # Ground truth writer
    _gt_writer = None   # type: GroundTruthWriter

    # file formats with support for EXIF
    _files_with_exif = ("JPEG", "PNG")

    ################################################################################################
    # Properties
    #

    # ==============================================================================================
    # render output format

    def update_render_output_format(self, context: bpy.types.Context) -> None:
        """Callback on render output format selection change.

        Arguments:
            context {bpy.types.Context} -- current context
        """
        context.scene.render.image_settings.file_format = self.render_output_format

    render_output_format: bpy.props.EnumProperty(
        name="File format",
        description="Rendering file format",
        items=[
            ("JPEG", "JPEG", "Output images in JPEG format", "FILE_IMAGE", 0),
            ("PNG", "PNG", "Output images in PNG format", "FILE_IMAGE", 1),
            ("BMP", "BMP", "Output images in bitmap format", "FILE_IMAGE", 2),
            ("AVI_JPEG", "AVI JPEG", "Output video in AVI JPEG format", "FILE_MOVIE", 3),
            ("AVI_RAW", "AVI Raw", "Output video in AVI JPEG format", "FILE_MOVIE", 4),
        ],
        update=update_render_output_format,
        options={'SKIP_SAVE'}
    )

    ################################################################################################
    # Layout
    #

    def draw(self, context: bpy.types.Context):
        """Operator panel layout"""
        layout = self.layout
        r = layout.split(factor=0.3, align=True)
        r.alignment = 'RIGHT'
        r.label(text="File format")
        r.prop(self, "render_output_format", text="")

        ff = self.render_output_format
        if ff not in SFMFLOW_OT_render_images._files_with_exif:
            r = layout.row()
            r.alert = True
            r.label(text="EXIF metadata will not be set for {} files".format(ff))

        r = layout.split(factor=0.3, align=True)
        r.alignment = 'RIGHT'
        r.label(text="Color")
        r.row().prop(context.scene.render.image_settings, "color_mode", expand=True)

        if ff == "PNG":
            r = layout.split(factor=0.3, align=True)
            r.alignment = 'RIGHT'
            r.label(text="Color depth")
            r.row().prop(context.scene.render.image_settings, "color_depth", expand=True)
            r = layout.split(factor=0.3, align=True)
            r.alignment = 'RIGHT'
            r.label(text="Compression")
            r.prop(context.scene.render.image_settings, "compression", text="", expand=True)
        elif ff != "AVI_RAW":
            r = layout.split(factor=0.3, align=True)
            r.alignment = 'RIGHT'
            r.label(text="Quality")
            r.prop(context.scene.render.image_settings, "quality", text="")

        r = layout.row()
        r.alignment = 'RIGHT'
        r.prop(context.scene.render, "use_overwrite")

    ################################################################################################
    # Behavior
    #

    # ==============================================================================================
    @classmethod
    def poll(cls, context: bpy.types.Context) -> bool:
        """Panel's enabling condition.
        The operator is enabled only if the scene has a render camera.

        Arguments:
            context {bpy.types.Context} -- poll context

        Returns:
            bool -- True to enable, False to disable
        """
        return context.scene.camera is not None

    # ==============================================================================================
    def invoke(self, context: bpy.types.Context, event: bpy.types.Event) -> set:  # pylint: disable=unused-argument
        """Init operator when called.

        Arguments:
            context {bpy.types.Context} -- invoke context
            event {bpy.types.Event} -- invoke event

        Returns:
            set -- enum set in {‘RUNNING_MODAL’, ‘CANCELLED’, ‘FINISHED’, ‘PASS_THROUGH’, ‘INTERFACE’}
        """
        if bpy.data.is_saved:
            if bpy.data.is_dirty:
                bpy.ops.wm.save_mainfile()
            # check exiftool version
            user_preferences = bpy.context.preferences
            addon_user_preferences_name = (__name__)[:__name__.index('.')]
            addon_prefs = user_preferences.addons[addon_user_preferences_name].preferences   # type: AddonPreferences
            exiftool_path = addon_prefs.exiftool_path
            if exiftool_path and "(-k)" in os.path.basename(exiftool_path):
                msg = "Error running `Exiftool`, please remove `(-k)` from filename"
                logger.error(msg)
                self.report({'ERROR'}, msg)
                return {'CANCELLED'}
            try:
                result = check_output([exiftool_path, "-ver"]).decode().rstrip()
                et_version = list(map(int, result.split('.')))
                if len(et_version) != 2 or et_version[0] < 10:
                    msg = "Error running `Exiftool`, version {} is not compatible".format(result)
                    logger.error(msg)
                    self.report({'ERROR'}, msg)
                    return {'CANCELLED'}
            except CalledProcessError as e:
                msg = "Error running `Exiftool` (exit code: {}, output: {}), check the path in user preferences".format(
                    e.returncode, e.output)
                logger.error(msg)
                self.report({'ERROR'}, msg)
                return {'CANCELLED'}
            except FileNotFoundError as e:
                msg = "Cannot find `Exiftool`, check the path in user preferences"
                logger.error(msg)
                self.report({'ERROR'}, msg)
                return {'CANCELLED'}

            # set file format
            ff = context.scene.render.image_settings.file_format
            self.render_output_format = ff if ff in ("JPEG", "PNG", "BMP", "AVI_JPEG", "AVI_RAW") else "JPEG"

            wm = context.window_manager
            return wm.invoke_props_dialog(self)
        #
        else:
            msg = "Save the project before rendering"
            logger.warning(msg)
            self.report({'WARNING'}, msg)
            return {'CANCELLED'}

    # ==============================================================================================
    def execute(self, context: bpy.types.Context) -> set:
        """Render current scene.

        Arguments:
            context {bpy.types.Context} -- current context

        Returns:
            set -- enum set in {‘CANCELLED’, ‘FINISHED’}
        """
        # cmd args handling
        if "--sfmflow_render" in sys.argv:
            i = sys.argv.index("--sfmflow_render") + 1
            if len(sys.argv) > i and (os.path.dirname(sys.argv[i]) != ''):
                context.scene.render.filepath = sys.argv[i]
            else:
                logger.error("A folder path must be specified after `--export_csv`")
                return {'CANCELLED'}
            name_suffix = "_cmd_"
            if "--sfmflow_motion_blur" in sys.argv:
                context.scene.render.use_motion_blur = True
                name_suffix += "-blur-"
            if "--sfmflow_dof" in sys.argv:
                context.scene.camera.data.dof.use_dof = True
                name_suffix += "-dof-"
            name_suffix += ".blend"

        # animate motion blur
        if context.scene.render.use_motion_blur:
            properties = context.scene.sfmflow
            animate_motion_blur(context.scene, properties.motion_blur_probability / 100, properties.motion_blur_shutter)

        # create ground truth writer
        SFMFLOW_OT_render_images._gt_writer = GroundTruthWriter(context.scene, context.scene.camera,
                                                                context.scene.render.filepath,
                                                                overwrite=context.scene.render.use_overwrite)

        # if executed form command line save new project file
        if "--sfmflow_render" in sys.argv:
            bpy.ops.wm.save_mainfile(filepath=(bpy.data.filepath + name_suffix))

        # start images rendering
        bpy.ops.render.render('INVOKE_DEFAULT', animation=True, use_viewport=False)
        return {'FINISHED'}

    # ==============================================================================================
    @staticmethod
    @persistent
    def render_complete_callback(scene: bpy.types.Scene) -> None:
        """Callback on frame rendered and saved to file.

        Arguments:
            scene {bpy.types.Scene} -- scene being rendered

        Raises:
            RuntimeError: if something goes wrong with ExifTool
        """
        logger.info("Rendering of frame %s completed.", scene.frame_current)
        scene.frame_set(scene.frame_current)   # update current frame to the rendered one
        #
        # --- update EXIF metadata
        ff = scene.render.image_settings.file_format
        if ff in SFMFLOW_OT_render_images._files_with_exif:
            logger.debug("Updating EXIF metadata")

            filepath = scene.render.frame_path(frame=scene.frame_current)
            user_preferences = bpy.context.preferences
            addon_user_preferences_name = (__name__)[:__name__.index('.')]
            addon_prefs = user_preferences.addons[addon_user_preferences_name].preferences   # type: AddonPreferences
            exiftool_path = addon_prefs.exiftool_path
            camera_data = scene.camera.data

            # compute 35mm focal length
            fl = camera_data.lens
            fl35 = 43.27 / sqrt(camera_data.sensor_width**2 + camera_data.sensor_height**2) * fl
            res_percent = scene.render.resolution_percentage / 100.

            # build exiftool command
            exiftool_cmd = [
                exiftool_path,
                "-exif:FocalLength={} mm".format(fl),
                "-exif:FocalLengthIn35mmFormat={}".format(int(fl35)),
                "-exif:Model=blender{}".format(int(camera_data.sensor_width)),
                "-exif:FocalPlaneXResolution={}".format(camera_data.sensor_width),
                "-exif:FocalPlaneYResolution={}".format(camera_data.sensor_height),
                "-exif:FocalPlaneResolutionUnit#=4",   # millimeters
                "-exif:ExifImageWidth={}".format(floor(scene.render.resolution_x * res_percent)),
                "-exif:ExifImageHeight={}".format(floor(scene.render.resolution_y * res_percent)),
                "-exif:ExifVersion=0230",   # some pipelines do not work with newer versions
                "-overwrite_original",
                filepath
            ]
            logger.info("Running ExifTool: %s", ' '.join(exiftool_cmd))

            # run exiftool
            try:
                exit_code = run(exiftool_cmd, timeout=5, check=False).returncode
            except TimeoutExpired:
                exit_code = -1
                logger.error("Timeout expired for EXIF metadata update!")
            except Exception as e:  # pylint: disable=broad-except
                logger.error("Exiftool execution exception: %s)", e)
            finally:
                if exit_code != 0:
                    msg = "Failed to set EXIF metadata for rendered frame '{}'".format(filepath)
                    logger.error(msg)
                    raise RuntimeError(msg)
                else:
                    logger.info("Metadata correctly set for frame '%s'", filepath)
        else:
            logger.debug("Skipping EXIF metadata update, not supported by %s format", ff)
        #
        # --- save camera pose ground truth
        SFMFLOW_OT_render_images._gt_writer.save_entry_for_current_frame()
        if scene.frame_current == scene.frame_end:
            SFMFLOW_OT_render_images._gt_writer.close()

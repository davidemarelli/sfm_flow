
import logging
import os
import sys
from math import degrees, floor, sqrt
from subprocess import CalledProcessError, TimeoutExpired, check_output, run
from typing import List, Tuple

import bpy
from bpy.app.handlers import persistent

from ..prefs import AddonPreferences
from ..utils import get_asset, set_blender_output_path
from ..utils.math import matrix_world_to_ypr

logger = logging.getLogger(__name__)


class SFMFLOW_OT_render_images(bpy.types.Operator):
    """Render dataset images, sets EXIF metadata and save camera poses file"""
    bl_idname = "sfmflow.render_images"
    bl_label = "Render dataset"

    # file formats with support for EXIF
    _files_with_exif = ("JPEG", "PNG")

    ################################################################################################
    # Properties
    #

    # ==============================================================================================
    # render camera

    def _get_render_cameras(self, context: bpy.types.Context) -> List[Tuple[str, str, str]]:
        """Get the list of available render cameras.

        Arguments:
            context {bpy.context} -- current context

        Returns:
            List[Tuple[str, str, str]] -- List of {EnumProperty} items
        """
        items = []
        for cp in context.scene.sfmflow.render_cameras:
            items.append((cp.camera.name, cp.camera.name, ""))
        items.sort(key=lambda t: t[1])   # sort by name
        return items

    render_camera: bpy.props.EnumProperty(
        name="Render camera",
        description="Available cameras for rendering",
        items=_get_render_cameras,
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
        r.label(text="Render camera")
        r.prop(self, "render_camera", text="")

        ff = context.scene.sfmflow.render_file_format
        if ff not in SFMFLOW_OT_render_images._files_with_exif:
            r = layout.row()
            r.alert = True
            r.label(text=f"EXIF metadata will not be set for {ff} files")
        else:
            r = layout.row(align=True)
            r.alignment = 'RIGHT'
            r.label(text="Write GPS Exif")
            r.prop(context.scene.sfmflow, "write_gps_exif", text="")

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
        return context.scene.sfmflow.has_render_camera()

    # ==============================================================================================
    def invoke(self, context: bpy.types.Context, event: bpy.types.Event) -> set:  # pylint: disable=unused-argument
        """Init operator when called.

        Arguments:
            context {bpy.types.Context} -- invoke context
            event {bpy.types.Event} -- invoke event

        Returns:
            set -- enum set in {‘RUNNING_MODAL’, ‘CANCELLED’, ‘FINISHED’, ‘PASS_THROUGH’, ‘INTERFACE’}
        """
        # use user selected file format for image rendering
        scene = context.scene
        scene.render.image_settings.file_format = scene.sfmflow.render_file_format
        #
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
                    msg = f"Error running `Exiftool`, version {result} is not compatible"
                    logger.error(msg)
                    self.report({'ERROR'}, msg)
                    return {'CANCELLED'}
            except CalledProcessError as e:
                msg = f"Error running `Exiftool` (exit code: {e.returncode}, output: {e.output})," \
                    " check the path in user preferences"
                logger.error(msg)
                self.report({'ERROR'}, msg)
                return {'CANCELLED'}
            except FileNotFoundError as e:
                msg = "Cannot find `Exiftool`, check the path in user preferences"
                logger.error(msg)
                self.report({'ERROR'}, msg)
                return {'CANCELLED'}

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
        scene = context.scene
        properties = scene.sfmflow
        #
        # cmd args handling
        if "--sfmflow_render" in sys.argv:
            i = sys.argv.index("--sfmflow_render") + 1
            if sys.argv[i] in scene.objects and scene.objects[sys.argv[i]].type == 'CAMERA':
                camera = scene.objects[sys.argv[i]]
            else:
                logger.error("A camera name must be specified after `--sfmflow_render`")
                return {'CANCELLED'}
            i += 1
            if len(sys.argv) > i and (os.path.dirname(sys.argv[i]) != ''):
                properties.output_path = sys.argv[i]
            else:
                logger.error("A folder path must be specified after `--sfmflow_render`")
                return {'CANCELLED'}
            name_suffix = "_cmd_"
            if "--sfmflow_motion_blur" in sys.argv:
                scene.sfmflow.use_motion_blur = True
                name_suffix += "-blur-"
            if "--sfmflow_dof" in sys.argv:
                camera.data.dof.use_dof = True
                name_suffix += "-dof-"
            if "--sfmflow_gps_exif" in sys.argv:
                properties.write_gps_exif = True
                name_suffix += "-gpsExif-"
            name_suffix += ".blend"
        else:
            camera = scene.objects[self.render_camera]   # set render camera

        # if executed form command line save new project file
        if "--sfmflow_render" in sys.argv:
            bpy.ops.wm.save_mainfile(filepath=(bpy.data.filepath + name_suffix))
            bpy.ops.sfmflow.export_cameras_gt('EXEC_DEFAULT')

        # start images rendering
        scene.camera = camera   # set render camera
        set_blender_output_path(properties.output_path, scene, camera)
        logger.info("Start rendering of camera: %s", camera.name)
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

            image_width = floor(scene.render.resolution_x * res_percent)
            image_height = floor(scene.render.resolution_y * res_percent)
            camera_maker = camera_data['sfmflow.maker'] if 'sfmflow.maker' in camera_data else ""
            camera_model = camera_data['sfmflow.model'] if 'sfmflow.model' in camera_data else ""

            # build exiftool command
            exiftool_cmd = [
                exiftool_path,
                "-config", get_asset("exiftool.config"),
                "-n",
                #
                f"-exif:FocalLength={fl}",
                f"-exif:FocalLengthIn35mmFormat={int(fl35)}",
                f"-exif:Make={camera_maker}",
                f"-exif:Model={camera_model}",
                f"-exif:FocalPlaneXResolution={(image_width / camera_data.sensor_width)}",
                f"-exif:FocalPlaneYResolution={(image_height / camera_data.sensor_height)}",
                "-exif:FocalPlaneResolutionUnit#=4",   # millimeters
                f"-exif:ExifImageWidth={image_width}",
                f"-exif:ExifImageHeight={image_height}"
            ]
            #
            if scene.sfmflow.write_gps_exif:   # include gps data
                camera = scene.camera
                u_scale = scene.unit_settings.scale_length     # unit scale
                position = camera.matrix_world.to_translation() * u_scale  # position in blender's reference system
                ypr = matrix_world_to_ypr(camera.matrix_world)   # get Yaw, Pitch, Roll angles
                yaw, pitch, roll = tuple(map(degrees, ypr))
                #
                yaw, pitch, roll = (yaw % 360), (pitch % 360), (roll % 360)
                yaw = 0. if yaw == 360. else yaw                # move in range [0, 359.999]
                pitch = pitch - (360. if pitch > 180. else 0)   # move in range [-180, +180]
                roll = roll - (360. if roll > 180. else 0)      # move in range [-180, +180]
                #
                exiftool_cmd += [
                    f"-XMP:GPSLatitude={position.y}",
                    f"-XMP:GPSLongitude={position.x}",
                    f"-XMP:GPSAltitude={position.z}",
                    "-XMP:GPSAltitudeRef=0",       # Above Sea Level
                    #
                    # "-XMP:GPSDOP=0.001",  # GPS accuracy
                    # "-XMP:GPSHPositioningError=0.001",  # GPS accuracy
                    # "-GPS:GPSDOP=0.001",  # GPS accuracy
                    # "-XMP-Camera:GPSXYAccuracy=0.001",
                    # "-XMP-Camera:GPSZAccuracy=0.001",
                    #
                    # "-GPS:GPSMapDatum=ENU",
                    # "-GPS:GPSLatitude={}".format(position.y),    # must be positive
                    # "-GPS:GPSLatitudeRef=N",       # North
                    # "-GPS:GPSLongitude={}".format(position.x),   # must be positive
                    # "-GPS:GPSLongitudeRef=E",      # East
                    f"-GPS:GPSAltitude={position.z}",
                    "-GPS:GPSAltitudeRef=0",       # Above Sea Level
                    "-GPS:GPSImgDirectionRef=T",   # True North
                    f"-GPS:GPSImgDirection={yaw}",  # yaw [0, 359.99]
                    f"-GPS:GPSPitch={pitch}",       # pitch [-180, +180]
                    # "-exif:CameraElevationAngle={}".format(pitch),   # pitch
                    f"-GPS:GPSRoll={roll}",         # roll -180 - +180
                ]
            #
            exiftool_cmd += [
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
                exit_code = -2
                logger.error("Exiftool execution exception: %s)", e)
            finally:
                if exit_code != 0:
                    msg = f"Failed to set EXIF metadata for rendered frame '{filepath}'"
                    logger.error(msg)
                    raise RuntimeError(msg)
                else:
                    logger.info("Metadata correctly set for frame '%s'", filepath)
        else:
            logger.debug("Skipping EXIF metadata update, not supported by %s format", ff)

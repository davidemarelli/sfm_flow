
import csv
import logging
import os
from math import acos, atan2, degrees, sqrt
from statistics import mean
from typing import Literal

import bpy
from mathutils import Vector
from sfm_flow.prefs import AddonPreferences
from sfm_flow.utils import (camera_detect_dof_distance, euclidean_distance, get_camera_lookat,
                            get_last_keyframe, get_render_image_filename)
from sfm_flow.utils.math import matrix_world_to_opk, matrix_world_to_ypr
from sfm_flow.utils.scene_bounding_box import SceneBoundingBox

logger = logging.getLogger(__name__)


class SFMFLOW_OT_export_cameras_gt(bpy.types.Operator):
    """Export render cameras ground truth"""
    bl_idname = "sfmflow.export_cameras_gt"
    bl_label = "Export cameras ground truth"

    # CSV field names in header for cameras ground truth
    CAMERA_CSV_FIELDNAMES = ("label",
                             "position_x", "position_y", "position_z",
                             "omega", "phi", "kappa",
                             "yaw", "pitch", "roll",
                             "rotation_w", "rotation_x", "rotation_y", "rotation_z",
                             "lookat_x", "lookat_y", "lookat_z",
                             "depth_of_field", "motion_blur",
                             "sun_azimuth", "sun_inclination",)

    # CSV field names in header for scene
    SCENE_CSV_FIELDNAMES = ("scene_name", "images_count",
                            "unit_system", "unit_length",
                            "scene_center_x", "scene_center_y", "scene_center_z",
                            "scene_ground_center_x", "scene_ground_center_y", "scene_ground_center_z",
                            "scene_width", "scene_depth", "scene_height",
                            "mean_cam_dist_center", "mean_cam_dist_obj", "mean_cam_height",)

    # format of floats in CSV file
    DIGITS = 6
    NUM_FORMAT = f"{{:.{DIGITS}f}}"

    ################################################################################################
    # Properties
    #

    # ==============================================================================================
    file_format: bpy.props.EnumProperty(
        name="File format",
        description="Cameras ground truth export file format",
        items=(
            ("file_format.csv", "CSV", ".csv file format"),
            ("file_format.tsv", "TSV", ".tsv file format"),
        ),
        default="file_format.csv"
    )

    ################################################################################################
    # Layout
    #

    def draw(self, context: bpy.types.Context):   # pylint: disable=unused-argument
        """Operator panel layout"""
        layout = self.layout
        row = layout.split(factor=0.33, align=True)
        row.label(text="File format")
        row.row().prop(self, "file_format", expand=True)

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
        # use user selected file format, ensures correct image filenames in exported files
        scene = context.scene
        scene.render.image_settings.file_format = scene.sfmflow.render_file_format
        #
        if bpy.data.is_saved:
            if bpy.data.is_dirty:
                # unsaved changes are present
                self.report({'WARNING'}, "Unsaved changes found, check and UNDO or SAVE changes before export")
                return {'CANCELLED'}

            return context.window_manager.invoke_props_dialog(self)
        else:
            self.report({'WARNING'}, "Save project before export")
            return {'CANCELLED'}

    # ==============================================================================================
    def execute(self, context: bpy.types.Context) -> set:
        """Export scene's and render cameras' ground truth.

        Arguments:
            context {bpy.types.Context} -- current context

        Returns:
            set -- enum set in {‘CANCELLED’, ‘FINISHED’}
        """
        scene = context.scene
        properties = scene.sfmflow
        export_folder = bpy.path.abspath(properties.output_path)
        os.makedirs(export_folder, exist_ok=True)
        #
        file_format = 'CSV' if self.file_format == "file_format.csv" else 'TSV'
        SFMFLOW_OT_export_cameras_gt.save_scene_infos(scene, export_folder, file_format)
        SFMFLOW_OT_export_cameras_gt.save_cameras_infos(scene, export_folder, file_format)
        #
        logger.info("Cameras ground truth exported.")
        return {'FINISHED'}

    ################################################################################################
    # Helper methods
    #

    # ==============================================================================================
    @staticmethod
    def save_scene_infos(scene: bpy.types.Scene, output_path: str, file_format: Literal['CSV', 'TSV']) -> None:
        """Write the CSV/TSV file containing infos about the scene:
            - scene's name
            - images count
            - measurement system unit
            - unit length
            - scene center coordinate
            - scene floor center coordinate, same as scene center but with z at its minimum
            - scene size (width, depth, height)
            - mean camera distance from scene center
            - mean camera-object intersection distance
            - mean camera height from the ground

        Arguments:
            scene {bpy.types.Scene} -- scene to export infos from
            output_path {str} -- output folder where to write the 'scene.*sv' file
            file_format {Literal['CSV', 'TSV']} -- export file format
        """
        logger.info("Saving scene info CSV/TSV")
        u_scale = scene.unit_settings.scale_length     # unit scale
        cameras = scene.sfmflow.get_render_cameras()
        #
        user_preferences = bpy.context.preferences
        addon_user_preferences_name = (__name__)[:__name__.index('.')]
        addon_prefs = user_preferences.addons[addon_user_preferences_name].preferences  # type: AddonPreferences
        #
        # get cameras animation end
        cameras_end_keyframes = []
        for camera in cameras:
            cameras_end_keyframes.append(get_last_keyframe(camera, True))
        #
        bbox = SceneBoundingBox(scene)
        bbox_center = bbox.center * u_scale
        bbox_floor_center = bbox.floor_center * u_scale
        #
        imgs_count = 0
        cam_dists_bbc = []
        cam_dists_objs = []
        cam_heights = []
        frame_backup = scene.frame_current
        for i in range(scene.frame_start, scene.frame_end+1):
            scene.frame_set(i)
            bpy.context.view_layer.update()  # make the frame change effective
            for camera, last_keyframe in zip(cameras, cameras_end_keyframes):
                if addon_prefs.limit_to_last_camera_keyframe and i > last_keyframe:
                    break   # skip since camera animation ends before scene's end_frame
                #
                imgs_count += 1
                cam_pos = camera.matrix_world.to_translation() * u_scale  # camera position
                cam_dists_bbc.append(euclidean_distance(bbox_center, cam_pos))
                cam_dists_objs.append(camera_detect_dof_distance(bpy.context.view_layer, camera, scene))
                cam_heights.append(cam_pos.z - bbox_floor_center.z)
        scene.frame_set(frame_backup)
        #
        row = (
            scene.name, imgs_count,
            #
            scene.unit_settings.system,
            scene.unit_settings.length_unit,
            # scene_center_...
            SFMFLOW_OT_export_cameras_gt.NUM_FORMAT.format(bbox_center.x),
            SFMFLOW_OT_export_cameras_gt.NUM_FORMAT.format(bbox_center.y),
            SFMFLOW_OT_export_cameras_gt.NUM_FORMAT.format(bbox_center.z),
            # scene_floor_center_...
            SFMFLOW_OT_export_cameras_gt.NUM_FORMAT.format(bbox_floor_center.x),
            SFMFLOW_OT_export_cameras_gt.NUM_FORMAT.format(bbox_floor_center.y),
            SFMFLOW_OT_export_cameras_gt.NUM_FORMAT.format(bbox_floor_center.z),
            # scene size
            SFMFLOW_OT_export_cameras_gt.NUM_FORMAT.format(bbox.width * u_scale),
            SFMFLOW_OT_export_cameras_gt.NUM_FORMAT.format(bbox.depth * u_scale),
            SFMFLOW_OT_export_cameras_gt.NUM_FORMAT.format(bbox.height * u_scale),
            # camera mean values
            SFMFLOW_OT_export_cameras_gt.NUM_FORMAT.format(mean(cam_dists_bbc)),
            SFMFLOW_OT_export_cameras_gt.NUM_FORMAT.format(mean(cam_dists_objs)),
            SFMFLOW_OT_export_cameras_gt.NUM_FORMAT.format(mean(cam_heights))
        )
        #
        if file_format == 'CSV':
            filename = "scene.csv"
            delimiter = ','
        else:   # TSV
            filename = "scene.tsv"
            delimiter = '\t'
        file_path = os.path.join(output_path, filename)
        with open(file_path, 'w', encoding='utf-8', newline='') as f:
            w = csv.writer(f, delimiter=delimiter, lineterminator='\r\n')
            w.writerow(SFMFLOW_OT_export_cameras_gt.SCENE_CSV_FIELDNAMES)
            w.writerow(row)
        logger.info("Saved scene info file %s.", file_path)

    # ==============================================================================================
    @staticmethod
    def save_cameras_infos(scene: bpy.types.Scene, output_path: str, file_format: Literal['CSV', 'TSV']) -> None:
        """Write the CSV/TSV file containing infos about the cameras poses.
        For each frame and each render camera:
            - image_name
            - position_(x,y,z)
            - rotation_(w,x,y,z)
            - lookat_(x,y,z)
            - depth_of_field
            - motion_blur
            - sun_azimuth  (only if the scene is lighted by sfmflow's sun driver)
            - sun_inclination  (only if the scene is lighted by sfmflow's sun driver)

        Arguments:
            scene {bpy.types.Scene} -- scene to export cameras ground truth from
            output_path {str} -- output folder where to write the 'cameras.*sv' file
            file_format {Literal['CSV', 'TSV']} -- export file format
        """
        logger.info("Saving cameras info CSV/TSV")
        u_scale = scene.unit_settings.scale_length     # unit scale
        cameras = scene.sfmflow.get_render_cameras()
        #
        user_preferences = bpy.context.preferences
        addon_user_preferences_name = (__name__)[:__name__.index('.')]
        addon_prefs = user_preferences.addons[addon_user_preferences_name].preferences  # type: AddonPreferences
        #
        # get cameras animation end
        cameras_end_keyframes = []
        for camera in cameras:
            cameras_end_keyframes.append(get_last_keyframe(camera, True))
        #
        frame_backup = scene.frame_current
        camera_backup = scene.camera
        #
        if file_format == 'CSV':
            filename = "cameras.csv"
            delimiter = ','
        else:   # TSV
            filename = "cameras.tsv"
            delimiter = '\t'
        file_path = os.path.join(output_path, filename)
        with open(file_path, 'w', encoding='utf-8', newline='') as f:
            w = csv.writer(f, delimiter=delimiter, lineterminator='\r\n')
            w.writerow(SFMFLOW_OT_export_cameras_gt.CAMERA_CSV_FIELDNAMES)
            #
            for frame in range(scene.frame_start, scene.frame_end+1):
                scene.frame_set(frame)
                #
                for camera, last_keyframe in zip(cameras, cameras_end_keyframes):
                    if addon_prefs.limit_to_last_camera_keyframe and frame > last_keyframe:
                        break   # skip since camera animation ends before scene's end_frame
                    #
                    scene.camera = camera   # set render camera
                    image_filename, _ = get_render_image_filename(camera, scene, frame)
                    #
                    position = camera.matrix_world.to_translation() * u_scale  # position in blender's reference system
                    rotation = camera.matrix_world.to_quaternion()      # rotation in blender's reference system
                    lookat = get_camera_lookat(camera)                  # lookat direction in blender's reference system
                    opk = matrix_world_to_opk(camera.matrix_world)   # get Omega, Phi, Kappa angles
                    ypr = matrix_world_to_ypr(camera.matrix_world)   # get Yaw, Pitch, Roll angles
                    omega, phi, kappa = tuple(map(degrees, opk))
                    yaw, pitch, roll = tuple(map(degrees, ypr))
                    yaw, pitch, roll = (yaw % 360), (pitch % 360), (roll % 360)
                    yaw = 0. if yaw == 360. else yaw                # move in range [0, 359.999]
                    pitch = pitch - (360. if pitch > 180. else 0)   # move in range [-180, +180]
                    roll = roll - (360. if roll > 180. else 0)      # move in range [-180, +180]
                    #
                    # get sun position
                    sun_rotation = None
                    sun_azimuth = None
                    sun_inclination = None
                    if "SunDriver" in scene.objects:
                        sun = scene.objects["SunDriver"]
                        if sun.rotation_mode == 'QUATERNION':
                            sun_rotation = sun.rotation_quaternion
                        else:
                            sun_rotation = sun.rotation_euler.to_quaternion()
                        sun_vector = Vector((0, 0, 1))   # zenith
                        sun_vector.rotate(sun_rotation)
                        sun_azimuth = atan2(sun_vector.y, sun_vector.x)
                        sun_inclination = acos(sun_vector.z / sqrt(sun_vector.x**2 + sun_vector.y**2 + sun_vector.z**2))
                    #
                    # save to file
                    has_blur = scene.render.use_motion_blur and (scene.render.motion_blur_shutter != 0.)
                    w.writerow((
                        image_filename,
                        # position
                        SFMFLOW_OT_export_cameras_gt.NUM_FORMAT.format(position.x),
                        SFMFLOW_OT_export_cameras_gt.NUM_FORMAT.format(position.y),
                        SFMFLOW_OT_export_cameras_gt.NUM_FORMAT.format(position.z),
                        # rotation OPK
                        SFMFLOW_OT_export_cameras_gt.NUM_FORMAT.format(omega),
                        SFMFLOW_OT_export_cameras_gt.NUM_FORMAT.format(phi),
                        SFMFLOW_OT_export_cameras_gt.NUM_FORMAT.format(kappa),
                        # rotation YPR
                        SFMFLOW_OT_export_cameras_gt.NUM_FORMAT.format(yaw),
                        SFMFLOW_OT_export_cameras_gt.NUM_FORMAT.format(pitch),
                        SFMFLOW_OT_export_cameras_gt.NUM_FORMAT.format(roll),
                        # rotation quaternion
                        SFMFLOW_OT_export_cameras_gt.NUM_FORMAT.format(rotation.w),
                        SFMFLOW_OT_export_cameras_gt.NUM_FORMAT.format(rotation.x),
                        SFMFLOW_OT_export_cameras_gt.NUM_FORMAT.format(rotation.y),
                        SFMFLOW_OT_export_cameras_gt.NUM_FORMAT.format(rotation.z),
                        # look-at
                        SFMFLOW_OT_export_cameras_gt.NUM_FORMAT.format(lookat.x),
                        SFMFLOW_OT_export_cameras_gt.NUM_FORMAT.format(lookat.y),
                        SFMFLOW_OT_export_cameras_gt.NUM_FORMAT.format(lookat.z),
                        # effects
                        camera.data.dof.use_dof,
                        has_blur,
                        # sun orientation
                        SFMFLOW_OT_export_cameras_gt.NUM_FORMAT.format(sun_azimuth) if sun_azimuth else None,
                        SFMFLOW_OT_export_cameras_gt.NUM_FORMAT.format(sun_inclination) if sun_inclination else None
                    ))
                    logger.debug("Saved pose ground truth for camera %s at frame %i.", camera.name, frame)
        #
        scene.frame_set(frame_backup)
        scene.camera = camera_backup
        #
        logger.info("Saved cameras info file %s.", file_path)
        return {'FINISHED'}

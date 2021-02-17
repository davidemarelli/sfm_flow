
import csv
import logging
import os
from statistics import mean

import bpy
from sfm_flow.utils import (camera_detect_dof_distance, euclidean_distance, get_camera_lookat,
                            get_render_image_filename)

from ..utils.scene_bounding_box import SceneBoundingBox

logger = logging.getLogger(__name__)


class SFMFLOW_OT_export_cameras_gt(bpy.types.Operator):
    """Export render cameras ground truth"""
    bl_idname = "sfmflow.export_cameras_gt"
    bl_label = "Export cameras"

    # CSV field names in header for cameras ground truth
    CAMERA_CSV_FIELDNAMES = ("image_name",
                             "position_x", "position_y", "position_z",
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
    NUM_FORMAT = "{{:.{}f}}".format(DIGITS)

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

            return self.execute(context)
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
        SFMFLOW_OT_export_cameras_gt.save_scene_infos(scene, export_folder)
        SFMFLOW_OT_export_cameras_gt.save_cameras_infos(scene, export_folder)
        #
        logger.info("Cameras ground truth exported.")
        return {'FINISHED'}

    ################################################################################################
    # Helper methods
    #

    # ==============================================================================================
    @staticmethod
    def save_scene_infos(scene: bpy.types.Scene, output_path: str) -> None:
        """Write the CSV file containing infos about the scene:
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
            output_path {str} -- output folder where to write the 'scene.csv' file
        """
        logger.info("Saving scene infos CSV")
        u_scale = scene.unit_settings.scale_length     # unit scale
        cameras = scene.sfmflow.get_render_cameras()
        #
        bbox = SceneBoundingBox(scene)
        bbox_center = bbox.center * u_scale
        bbox_floor_center = bbox.floor_center * u_scale
        #
        cam_dists_bbc = []
        cam_dists_objs = []
        cam_heights = []
        frame_backup = scene.frame_current
        for i in range(scene.frame_start, scene.frame_end+1):
            scene.frame_set(i)
            bpy.context.view_layer.update()  # make the frame change effective
            for camera in cameras:
                cam_pos = camera.matrix_world.to_translation() * u_scale  # camera position
                cam_dists_bbc.append(euclidean_distance(bbox_center, cam_pos))
                cam_dists_objs.append(camera_detect_dof_distance(bpy.context.view_layer, camera, scene))
                cam_heights.append(cam_pos.z - bbox_floor_center.z)
        scene.frame_set(frame_backup)
        #
        row = (
            scene.name, (scene.frame_end - scene.frame_start + 1),
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
        file_path = os.path.join(output_path, "scene.csv")
        with open(file_path, 'w', newline='') as f:
            w = csv.writer(f, delimiter=',')
            w.writerow(SFMFLOW_OT_export_cameras_gt.SCENE_CSV_FIELDNAMES)
            w.writerow(row)
        logger.info("Saved scene infos file %s.", file_path)

    # ==============================================================================================
    @staticmethod
    def save_cameras_infos(scene: bpy.types.Scene, output_path: str) -> None:
        """Write the CSV file containing infos about the cameras poses.
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
            output_path {str} -- output folder where to write the 'cameras.csv' file
        """
        u_scale = scene.unit_settings.scale_length     # unit scale
        cameras = scene.sfmflow.get_render_cameras()
        #
        frame_backup = scene.frame_current
        camera_backup = scene.camera
        #
        csv_file_path = os.path.join(output_path, "cameras.csv")
        with open(csv_file_path, 'w', newline='') as csvfile:
            w = csv.writer(csvfile, delimiter=',')
            w.writerow(SFMFLOW_OT_export_cameras_gt.CAMERA_CSV_FIELDNAMES)
            #
            for frame in range(scene.frame_start, scene.frame_end+1):
                scene.frame_set(frame)
                #
                for camera in cameras:
                    scene.camera = camera   # set render camera
                    image_filename, _ = get_render_image_filename(camera, scene, frame)
                    #
                    position = camera.matrix_world.to_translation() * u_scale  # position in blender's reference system
                    rotation = camera.matrix_world.to_quaternion()      # rotation in blender's reference system
                    lookat = get_camera_lookat(camera)                  # lookat direction in blender's reference system
                    #
                    # get sun position
                    sun_rotation = None
                    if "SunDriver" in scene.objects:
                        sun = scene.objects["SunDriver"]
                        if sun.rotation_mode == 'QUATERNION':
                            sun_rotation = sun.rotation_quaternion
                        else:
                            sun_rotation = sun.rotation_euler.to_quaternion()
                    #
                    # save to file
                    has_blur = scene.render.use_motion_blur and (scene.render.motion_blur_shutter != 0.)
                    w.writerow((image_filename, position, rotation, lookat,
                                camera.data.dof.use_dof, has_blur, sun_rotation))
                    logger.debug("Saved pose ground truth for camera %s at frame %i.", camera.name, frame)
        #
        scene.frame_set(frame_backup)
        scene.camera = camera_backup
        #
        logger.info("GCPs exported.")
        return {'FINISHED'}

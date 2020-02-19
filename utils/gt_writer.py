
import csv
import logging
import os
from math import acos, atan2, sqrt
from statistics import mean

import bpy
from mathutils import Quaternion, Vector
from sfm_flow.utils import camera_detect_dof_distance, euclidean_distance, get_camera_lookat

from .scene_bounding_box import SceneBoundingBox

logger = logging.getLogger(__name__)


class GroundTruthWriter():
    """Ground truth writing functions."""

    # CSV field names in header for cameras ground truth
    CAMERA_CSV_FIELDNAMES = ("image_number",
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
    # Constructor and destructor
    #

    # ==============================================================================================
    def __init__(self, scene: bpy.types.Scene, camera: bpy.types.Camera, folder_path: str,
                 overwrite: bool = False, delimiter: str = ','):
        """Create a ground truth CSV writer object.

        Arguments:
            scene {bpy.types.Scene} -- blender scene
            camera {bpy.types.Camera} -- render camera
            folder_path {str} -- folder, where to save the CSV file

        Keyword Arguments:
            overwrite {bool} -- if {True} the file will be overwritten if already exists (default: {False})
            delimiter {str} -- CSV fields delimiter (default: {','})
        """
        self.scene = scene
        self.camera = camera
        #
        self.folder_path = bpy.path.abspath(folder_path)
        os.makedirs(self.folder_path, exist_ok=True)
        self.file_path = os.path.join(self.folder_path, "cameras.csv")
        self.overwrite = overwrite
        #
        # remove gt camera file if overwrite enabled
        if overwrite and os.path.exists(self.file_path) and os.path.isfile(self.file_path):
            os.remove(self.file_path)
        #
        self.file = open(self.file_path, 'a', newline='')
        self.writer = csv.writer(self.file, delimiter=delimiter)
        self.delimiter = delimiter
        if overwrite:
            self.writer.writerow(GroundTruthWriter.CAMERA_CSV_FIELDNAMES)
        #
        self.save_scene_infos()

    # ==============================================================================================
    def __del__(self):
        """Assure that the file is closed."""
        if hasattr(self, "file"):   # avoid call if errors in __init__
            self.close()

    ################################################################################################
    # Methods
    #

    # ==============================================================================================
    def close(self) -> None:
        """Close CSV file if needed."""
        if self.file:
            self.file.close()
            self.file = None

    # ==============================================================================================
    def save_scene_infos(self) -> None:
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
        """
        logger.info("Saving scene infos CSV")
        u_scale = self.scene.unit_settings.scale_length     # unit scale
        file_path = os.path.join(self.folder_path, "scene.csv")
        #
        # remove ground truth camera file if overwrite enabled
        if self.overwrite and os.path.exists(file_path) and os.path.isfile(file_path):
            os.remove(file_path)
        #
        bbox = SceneBoundingBox(self.scene)
        bbox_center = bbox.center * u_scale
        bbox_floor_center = bbox.floor_center * u_scale
        #
        cam_dists_bbc = []
        cam_dists_objs = []
        cam_heights = []
        for i in range(self.scene.frame_start, self.scene.frame_end+1):
            self.scene.frame_set(i)
            bpy.context.view_layer.update()  # make the frame change effective
            cam_pos = self.camera.matrix_world.to_translation() * u_scale  # cam position
            cam_dists_bbc.append(euclidean_distance(bbox_center, cam_pos))
            cam_dists_objs.append(camera_detect_dof_distance(bpy.context.view_layer, self.camera, self.scene))
            cam_heights.append(cam_pos.z - bbox_floor_center.z)
        #
        row = (
            self.scene.name, (self.scene.frame_end - self.scene.frame_start + 1),
            #
            self.scene.unit_settings.system,
            self.scene.unit_settings.length_unit,
            # scene_center_...
            GroundTruthWriter.NUM_FORMAT.format(bbox_center.x),
            GroundTruthWriter.NUM_FORMAT.format(bbox_center.y),
            GroundTruthWriter.NUM_FORMAT.format(bbox_center.z),
            # scene_floor_center_...
            GroundTruthWriter.NUM_FORMAT.format(bbox_floor_center.x),
            GroundTruthWriter.NUM_FORMAT.format(bbox_floor_center.y),
            GroundTruthWriter.NUM_FORMAT.format(bbox_floor_center.z),
            # scene size
            GroundTruthWriter.NUM_FORMAT.format(bbox.width * u_scale),
            GroundTruthWriter.NUM_FORMAT.format(bbox.depth * u_scale),
            GroundTruthWriter.NUM_FORMAT.format(bbox.height * u_scale),
            # camera mean values
            GroundTruthWriter.NUM_FORMAT.format(mean(cam_dists_bbc)),
            GroundTruthWriter.NUM_FORMAT.format(mean(cam_dists_objs)),
            GroundTruthWriter.NUM_FORMAT.format(mean(cam_heights))
        )
        with open(file_path, 'a', newline='') as f:
            w = csv.writer(f, delimiter=self.delimiter)
            if f.tell() == 0:
                w.writerow(GroundTruthWriter.SCENE_CSV_FIELDNAMES)
            try:
                w.writerow(row)
            except csv.Error as e:
                msg = "Error writing CSV file: {}".format(e)
                logger.error(msg)
        logger.info("Saved scene infos file %s.", file_path)

    # ==============================================================================================
    def save_entry_for_current_frame(self) -> None:
        """Write the CSV row for the current scene's frame."""
        frame_number = self.scene.frame_current
        logger.debug("Saving camera pose ground truth, frame %i.", frame_number)
        #
        # get camera params
        position = self.camera.matrix_world.to_translation()  # position in blender's reference system
        position *= self.scene.unit_settings.scale_length     # apply scale
        rotation = self.camera.matrix_world.to_quaternion()   # rotation in blender's reference system
        lookat = get_camera_lookat(self.camera)               # lookat direction in blender's reference system
        #
        # get sun position
        sun_rotation = None
        if "SunDriver" in self.scene.objects:
            sun = self.scene.objects["SunDriver"]
            if sun.rotation_mode == 'QUATERNION':
                sun_rotation = sun.rotation_quaternion
            else:
                sun_rotation = sun.rotation_euler.to_quaternion()
        #
        # save to file
        has_blur = self.scene.render.use_motion_blur and (self.scene.render.motion_blur_shutter != 0.)
        self._write_gt_row(frame_number, position, rotation,
                           lookat, self.camera.data.dof.use_dof, has_blur, sun_rotation)
        logger.info("Saved camera pose ground truth, frame %i.", frame_number)

    # ==============================================================================================
    def save_entry_for_all_frames(self) -> None:
        """Write the CSV entries for all the frames in scene animation."""
        for i in range(self.scene.frame_start, self.scene.frame_end+1):
            self.scene.frame_set(i)
            bpy.context.view_layer.update()  # make the frame change effective
            self.save_entry_for_current_frame()

    ################################################################################################
    # Helpers
    #

    # ==============================================================================================
    def _write_gt_row(self, frame_number: int, position: Vector, rotation: Quaternion, lookat: Vector,
                      dof: bool, motion_blur: bool, sun_rotation: Quaternion) -> None:
        """Internal helper. Build and write a single CSV row to the file.

        Arguments:
            frame_number {int} -- number of the frame / image
            position {Vector} -- position of the render camera
            rotation {Quaternion} -- rotation of the render camera
            lookat {Vector} -- look-at direction of the render camera
            dof {bool} -- depth of field presence flag
            motion_blur {bool} -- motion blur presence flag
            sun_rotation {Quaternion} -- sun rotation if defined, {None} otherwise
        """
        # get sun azimuth and inclination
        sun_azimuth = None
        sun_inclination = None
        if sun_rotation:
            sun_vector = Vector((0, 0, 1))   # zenith
            sun_vector.rotate(sun_rotation)
            sun_azimuth = atan2(sun_vector.y, sun_vector.x)
            sun_inclination = acos(sun_vector.z / sqrt(sun_vector.x**2 + sun_vector.y**2 + sun_vector.z**2))
        #
        row = (
            # frame number
            "{0:0>4}".format(frame_number),
            # camera position
            GroundTruthWriter.NUM_FORMAT.format(position.x),
            GroundTruthWriter.NUM_FORMAT.format(position.y),
            GroundTruthWriter.NUM_FORMAT.format(position.z),
            # camera rotation
            GroundTruthWriter.NUM_FORMAT.format(rotation.w),
            GroundTruthWriter.NUM_FORMAT.format(rotation.x),
            GroundTruthWriter.NUM_FORMAT.format(rotation.y),
            GroundTruthWriter.NUM_FORMAT.format(rotation.z),
            # camera look-at
            GroundTruthWriter.NUM_FORMAT.format(lookat.x),
            GroundTruthWriter.NUM_FORMAT.format(lookat.y),
            GroundTruthWriter.NUM_FORMAT.format(lookat.z),
            # depth of field
            dof,
            # motion blur
            motion_blur,
            #
            # sun orientation
            GroundTruthWriter.NUM_FORMAT.format(sun_azimuth),
            GroundTruthWriter.NUM_FORMAT.format(sun_inclination),
        )
        try:
            self.writer.writerow(row)
            self.file.flush()
        except csv.Error as e:
            msg = "Error writing CSV file: {}".format(e)
            logger.error(msg)

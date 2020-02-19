
import logging
from operator import itemgetter
from statistics import mean, stdev
from typing import Dict, List, Tuple
from uuid import uuid1

import bgl
import bpy
from mathutils import Matrix, Vector
from mathutils.kdtree import KDTree
from sfm_flow.utils import get_reconstruction_collection

from .camera import ReconCamera
from .point_cloud import PointCloud

logger = logging.getLogger(__name__)


class ReconModel():
    """Single reconstructed model.
    Description of a reconstructed 3D model, contains information about reconstructed cameras and 3D points.
    """

    ################################################################################################
    # Properties
    #

    @property
    def is_removed(self) -> bool:
        """The status of the model, shown/removed from the scene. Read only.

        Returns:
            bool -- True if the model is no longer in use
        """
        return self._is_removed

    ################################################################################################
    # Constructor
    #

    # ==============================================================================================
    def __init__(self, name: str, point_cloud: PointCloud = None):

        # model name
        self.name = name

        # UUID (objects names aren't unique, use an uuid for each model)
        self.uuid = str(uuid1())

        # cameras
        self.number_of_cameras = 0   # type: int
        self.cameras = []            # type: List[ReconCamera]

        # 3D point cloud
        self.point_cloud = point_cloud   # type: PointCloud

        # presence of associated PLY models
        self.has_ply_file = False    # type: bool

        # UI element to manually control the model
        self._ui_control_empty = None   # type: Object

        # transformation matrix of the initial reconstructed model centroid
        self._initial_centroid_matrix = None   # type: Matrix

        self._draw_handler_obj = None

        # internal flag, {True} after the model has been removed from the UI (_ui_control_empty has been deleted)
        self._is_removed = False   # type: bool

        # 3D view space data
        self._space_view_3d = bpy.types.SpaceView3D

    # ==============================================================================================
    def free(self) -> None:
        """Release resources, prepare for destruction!"""
        if self._draw_handler_obj and self._space_view_3d:
            logger.debug("Removing draw handler for 3D reconstruction model '%s'", self.name)
            handler = self._draw_handler_obj
            self._draw_handler_obj = None
            self._space_view_3d.draw_handler_remove(handler, 'WINDOW')

    ################################################################################################
    # Methods
    #

    # ==============================================================================================

    def select_set(self, state: bool) -> None:
        """Select/deselect the model.

        Arguments:
            state {bool} -- Selected if {True}, deselected otherwise
        """
        self._ui_control_empty.select_set(state)

    # ==============================================================================================
    def set_active(self, context: bpy.types.Context) -> None:
        """Set the model as the active object in the viewport.

        Arguments:
            context {bpy.types.Context} -- current context
        """
        context.view_layer.objects.active = self._ui_control_empty

    # ==============================================================================================
    def register_model(self, target_pc: List[Vector], gt_kdtree: KDTree, max_iterations: int = None,
                       samples: int = None, use_filtered_cloud: bool = True) -> float:
        """Register the model to the ground truth.

        Arguments:
            target_pc {List[Vector]} -- target/reference point cloud

        Keyword Arguments:
            max_iterations {int} -- number of iteration allowed (default: {None} 1% of point cloud size, min 100)
            samples {int} -- percentage of points to be used for alignment (default: {None},
                             25% of point cloud size, min 10000)

        Returns:
            float  -- registration error
        """
        initial_align_matrix = self._ui_control_empty.matrix_world @ self._initial_centroid_matrix
        #
        # number of samples for alignment
        if not samples:
            # 10000 minimum, max 10% of total available points
            samples = max(10000, int(len(self.point_cloud.vertices)*.25))
        else:
            samples = int(len(self.point_cloud.vertices)*samples/100)
        #
        # number of allowed iterations
        if not max_iterations:
            max_iterations = samples // 100
        #
        registration_matrix, error = self.point_cloud.get_regsitration_to_target(target_pc, initial_align_matrix,
                                                                                 target_pc_kdtree=gt_kdtree,
                                                                                 max_iterations=max_iterations,
                                                                                 samples=samples,
                                                                                 use_filtered_cloud=use_filtered_cloud)
        self.apply_registration_matrix(registration_matrix)
        # self.show()   # update the viewport, cannot run in a thread
        return error

    # ==============================================================================================
    def apply_registration_matrix(self, matrix: Matrix) -> None:
        """Register the model to the ground truth using a given matrix.

        Arguments:
            matrix {Matrix} -- registration matrix
        """
        self._ui_control_empty.matrix_world = matrix @ self._ui_control_empty.matrix_world

    # ==============================================================================================
    def filter_model(self, target_pc_kdtree: KDTree, distance_threshold: float) -> None:
        """Filter the reconstructed point cloud.

        Arguments:
            target_pc_kdtree {KDTree} -- target/reference point cloud KDTree
            distance_threshold {float} -- maximum allowed distance
        """
        initial_align_matrix = self._ui_control_empty.matrix_world @ self._initial_centroid_matrix
        self.point_cloud.filter_point_cloud(target_pc_kdtree, initial_align_matrix, distance_threshold)
        self.show()   # update the viewport

    # ==============================================================================================
    def filter_model_clear(self) -> None:
        """Clear the current point cloud filtering."""
        self.point_cloud.clear_filtered_cloud()
        self.show()   # update the viewport

    # ==============================================================================================
    def has_filter_model(self) -> None:
        """Check if the model has an active filtering."""
        return self.point_cloud.has_filtered_cloud()

    # ==============================================================================================
    def add_camera(self, recon_camera: ReconCamera) -> None:
        """Add a reconstructed camera to the model.

        Arguments:
            recon_camera {ReconCamera} -- reconstructed camera
        """
        self.cameras.append(recon_camera)

    # ==============================================================================================
    def show(self) -> None:
        """Setup required data to show the reconstructed model.
        Cannot be run from thread (unusable with {sfm_flow.operators.ThreadedOperator}).
        """
        if self._ui_control_empty is None:
            collection = get_reconstruction_collection()
            #
            # use an empty object as an UI control for manipulating the point cloud
            # since the empty origin correspond to the empty location, use the translation transformation
            # to take into account the initial cloud and empty location
            self._ui_control_empty = bpy.data.objects.new(self.name, None)
            collection.objects.link(self._ui_control_empty)
            self._ui_control_empty.show_name = True
            #
            # set the model uuid to the UI object for later checks.
            # here we avoid usage of a bpy.types.Object.sfmflow_model_uuid because this property is
            # used only for reconstruction rendering
            self._ui_control_empty['sfmflow_model_uuid'] = self.uuid
            #
            cloud_center = self.point_cloud.center
            self._ui_control_empty.location = cloud_center  # use `location`, is not possible to set origin of empty
            self._initial_centroid_matrix = Matrix.Translation(cloud_center).inverted()
        if self._draw_handler_obj:
            bpy.types.SpaceView3D.draw_handler_remove(self._draw_handler_obj, 'WINDOW')
        #
        # init point cloud drawing
        if self.point_cloud:
            self.point_cloud.show(self._ui_control_empty.matrix_world, self._initial_centroid_matrix,
                                  self._ui_control_empty.sfmflow.cloud_filtering_display_mode)
        #
        # init cameras drawing
        for camera in self.cameras:
            camera.show(self._ui_control_empty.matrix_world, self._initial_centroid_matrix)
        #
        self._draw_handler_obj = self._space_view_3d.draw_handler_add(self._draw_handler, (), 'WINDOW', 'POST_VIEW')
        #
        # update the view layer
        self._ui_control_empty.hide_set(False)   # force cloud redraw
        # bpy.context.view_layer.update() is not helpful to solve some cases...

    # ==============================================================================================
    def _draw_handler(self) -> None:
        """Model draw function, to be called by a {SpaceView3D} draw_handler (self.draw_handler)."""
        if self._draw_handler_obj:
            # get the model UI handle, if exists
            ui_handle = next((o for o in bpy.data.objects if ('sfmflow_model_uuid' in o)
                              and (o['sfmflow_model_uuid'] == self.uuid)), None)
            self._ui_control_empty = ui_handle

            if ui_handle and ui_handle.visible_get():  # ui handle exists and is visible
                # enable/disable OPENGL features
                if ui_handle.sfmflow.show_recon_always:
                    bgl.glDisable(bgl.GL_DEPTH_TEST)
                else:
                    bgl.glEnable(bgl.GL_DEPTH_TEST)
                # render point cloud
                self.point_cloud.draw(ui_handle.matrix_world)
                # render cameras
                if ui_handle.sfmflow.show_recon_cameras:
                    for cam in self.cameras:
                        cam.draw(ui_handle.matrix_world)
            #
            elif not ui_handle:                        # ui handle doesn't exists, remove model from rendering
                # create a local copy, set `self.draw_handler` to {None} to avoid multiple `draw_handler_remove` calls
                handler = self._draw_handler_obj
                self._draw_handler_obj = None
                # delete cameras and point cloud
                del self.point_cloud
                del self.cameras
                self._space_view_3d.draw_handler_remove(handler, 'WINDOW')
                # flag self for removal, will be removed later by {ReconstructionsManager}
                self._is_removed = True

    # ==============================================================================================
    def evaluate(self, scene: bpy.types.Scene, target_pc_kdtree: KDTree,
                 use_filtered_cloud: bool = True) -> Tuple[Dict, Dict]:
        """Evaluate the reconstructed 3D model. Run both point cloud evaluation and camera poses evaluation.

        Arguments:
            scene {bpy.types.Scene} -- ground truth scene
            target_pc_kdtree {KDTree} -- target/reference point cloud KDTree
            use_filtered_cloud {bool} -- if {True} the filtered point cloud is used for evaluation,
                                         the whole cloud otherwise

        Returns:
            dict -- point cloud evaluation results, see PointCloud.evaluate()
            dict -- camera poses evaluation results dictionary:
                    'pos_mean' {float}: mean position difference
                    'pos_std' {float}: position difference standard deviation
                    'pos_min' {float}: minimum position difference
                    'pos_max' {float}: maximum position difference
                    'lookat_mean' {float}: mean camera lookat orientation difference
                    'lookat_std' {float}: camera lookat orientation difference standard deviation
                    'lookat_min' {float}: minimum camera lookat orientation difference
                    'lookat_max' {float}: maximum camera lookat orientation difference
                    'rot_mean' {float}: mean camera orientation difference
                    'rot_std' {float}: camera orientation difference standard deviation
                    'rot_min' {float}: minimum camera orientation difference
                    'rot_max' {float}: maximum camera orientation difference
                    'camera_count' {float}: ground truth cameras count
                    'reconstructed_camera_count' {float}: reconstructed and evaluated cameras count
                    'reconstructed_camera_percent' {float}: percentage of reconstructed cameras
        """
        # point cloud evaluation
        pc_result = self.point_cloud.evaluate(target_pc_kdtree, use_filtered_cloud)
        #
        # camera poses evaluation
        current_frame = scene.frame_current
        cam_results = [c.evaluate(scene) for c in self.cameras]
        scene.frame_current = current_frame
        # FIXME this is awful  ¯\_(ツ)_/¯
        cam_pos_dists = list(map(itemgetter('position_distance'), cam_results))
        cam_lookat_diffs = list(map(itemgetter('lookat_difference_deg'), cam_results))
        cam_rot_diffs = list(map(itemgetter('rotation_difference_deg'), cam_results))
        #
        gt_camera_count = (scene.frame_end - scene.frame_start + 1) // scene.frame_step
        pos_mean = mean(cam_pos_dists)
        lookat_mean = mean(cam_lookat_diffs)
        rot_mean = mean(cam_rot_diffs)
        cam_result = {
            "pos_mean": pos_mean,
            "pos_std": stdev(cam_pos_dists, pos_mean) if len(cam_pos_dists) > 1 else 0.,
            "pos_min": min(cam_pos_dists),
            "pos_max": max(cam_pos_dists),
            "lookat_mean": lookat_mean,
            "lookat_std": stdev(cam_lookat_diffs, lookat_mean) if len(cam_lookat_diffs) > 1 else 0.,
            "lookat_min": min(cam_lookat_diffs),
            "lookat_max": max(cam_lookat_diffs),
            "rot_mean": rot_mean,
            "rot_std": stdev(cam_rot_diffs, rot_mean) if len(cam_rot_diffs) > 1 else 0.,
            "rot_min": min(cam_rot_diffs),
            "rot_max": max(cam_rot_diffs),
            "camera_count": gt_camera_count,
            "reconstructed_camera_count": len(self.cameras),
            "reconstructed_camera_percent": len(self.cameras) / gt_camera_count
        }
        #
        return pc_result, cam_result

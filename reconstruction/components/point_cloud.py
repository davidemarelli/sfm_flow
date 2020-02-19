
import logging
from functools import reduce
from random import shuffle
from statistics import mean, stdev
from typing import Dict, List, Tuple, Union

import numpy as np

import bpy
from gpu.types import GPUShader
from gpu_extras.batch import batch_for_shader
from mathutils import Color, Matrix, Vector
from mathutils.kdtree import KDTree
from sfm_flow.utils import euclidean_distance

logger = logging.getLogger(__name__)


class PointCloud():
    """Point cloud representation.
    Includes the actual 3D points and the methods to render them in the 3D view.
    """

    # point cloud vertex shader
    _vertex_shader = '''
        in vec3 position;
        in vec3 color;
        uniform mat4 perspective_matrix;
        uniform mat4 object_matrix;
        uniform mat4 initial_centroid_matrix;
        out vec4 f_color;
        void main() {
            gl_Position = perspective_matrix * object_matrix * initial_centroid_matrix * vec4(position, 1.0f);
            f_color = vec4(color[0], color[1], color[2], 1.0f);
        }
    '''

    # point cloud fragment shader
    _fragment_shader = '''
        in vec4 f_color;
        out vec4 fragColor;
        void main() {
            fragColor = f_color;
        }
    '''

    ################################################################################################
    # Properties
    #

    # ==============================================================================================
    @property
    def center(self) -> Vector:
        """The current centroid of the point cloud. Computed on-the-fly.

        Returns:
            Vector -- centroid 3D coordinates
        """
        return np.mean(self.vertices, axis=0)

    # ==============================================================================================
    @property
    def vertices_filtered(self) -> np.ndarray:
        """Get the filtered point cloud.

        Returns:
            np.ndarray -- filtered vertices
        """
        mask = np.ones(len(self.vertices), dtype=bool)
        mask[self._discard_vertices] = False
        return self.vertices[mask]

    # ==============================================================================================
    @property
    def colors_filtered(self) -> np.ndarray:
        """Get the filtered colors.

        Returns:
            np.ndarray -- filtered vertices colors
        """
        mask = np.ones(len(self.colors), dtype=bool)
        mask[self._discard_vertices] = False
        return self.colors[mask]

    ################################################################################################
    # Constructor
    #

    def __init__(self, point_count: int):

        # number of points in the cloud
        self.point_count = point_count   # type: int

        # the points
        self.vertices = np.empty((point_count, 3), dtype=np.float32)   # type: np.ndarray

        # the colors of the points, range [0-1]
        self.colors = np.empty((point_count, 3), dtype=np.float32)     # type: np.ndarray

        # indices of vertices discarded during point cloud filtering
        self._discard_vertices = []                                    # type: List[int]

        # point cloud filter distance threshold
        self._filter_distance = float('inf')                           # type: float

        # last point set in the cloud
        self._last_point_set = -1                                      # type: int

        # point cloud object matrix, to be set to UI control element world_matrix
        self._object_matrix = None   # type: Matrix

        # initial centroid translation matrix
        self._initial_centroid_matrix = None   # type: Matrix

        self._shader = None   # type: GPUShader
        self._batch = None    # type: GPUBatch

        user_preferences = bpy.context.preferences
        addon_user_preferences_name = (__name__)[:__name__.index('.')]
        prefs = user_preferences.addons[addon_user_preferences_name].preferences   # type: AddonPreferences
        self.filtered_points_color = np.array(prefs.filtered_points_color)   # type: np.ndarray

    ################################################################################################
    # Methods
    #

    # ==============================================================================================
    def add_point(self, position: Vector, color: Color) -> None:
        """Add a reconstructed vertex to the cloud.

        Arguments:
            position {Vector} -- reconstructed point coordinates
            color {Color} -- reconstructed point color in range [0-1]

        Raises:
            RuntimeError: when trying to set more points than the cloud size
        """
        if self._last_point_set + 1 >= self.point_count:
            raise RuntimeError("Trying to set more points than cloud dimensions!")
        self._last_point_set += 1

        self.vertices[self._last_point_set, :] = position[0:3]   # load vertex coordinates
        self.colors[self._last_point_set, :] = color[0:3]        # load colors

    # ==============================================================================================
    def show(self, object_matrix: Matrix, initial_centroid_matrix: Matrix, filtering_display_mode: str) -> None:
        """Setup shaders and other required data to display the point cloud.

        Arguments:
            object_matrix {bpy.types.Object} -- user interface handle object matrix
            initial_centroid_matrix {Matrix} -- initial centroid matrix of the recontruction
            filtering_display_mode {str} -- point cloud filtering diplay mode,
                                            from {sfm_flow.reconstruction.SFMFLOW_ReconstructionModelProperties}
        """
        if filtering_display_mode == "cloud_filter.color":
            # override colors for discarded points
            positions = self.vertices
            colors = self.colors.copy()
            colors[self._discard_vertices] = self.filtered_points_color
        elif filtering_display_mode == "cloud_filter.filtered":
            # show only points that are not discarded
            positions = self.vertices_filtered
            colors = self.colors_filtered
        else:  # default to "cloud_filter.all"
            # show all vertices with original colors
            positions = self.vertices
            colors = self.colors
        #
        # setup shader
        self._shader = GPUShader(PointCloud._vertex_shader, PointCloud._fragment_shader)
        self._batch = batch_for_shader(self._shader, 'POINTS', {"position": positions, "color": colors},)
        self._object_matrix = object_matrix
        self._initial_centroid_matrix = initial_centroid_matrix

    # ==============================================================================================
    def draw(self, object_matrix: Matrix = None) -> None:
        """Point cloud draw function, to be called by a {SpaceView3D} draw_handler.

        Keyword Arguments:
            object_matrix {Matrix} -- optional matrix_world of the UI empty (default: {None})
        """
        if object_matrix:
            self._object_matrix = object_matrix
        #
        self._batch.draw(self._shader)
        self._shader.bind()
        self._shader.uniform_float("perspective_matrix", bpy.context.region_data.perspective_matrix)
        self._shader.uniform_float("object_matrix", self._object_matrix)
        self._shader.uniform_float("initial_centroid_matrix", self._initial_centroid_matrix)

    # ==============================================================================================
    def _show_as_vertices_mesh(self, vertices: Union[np.array, List[Vector]] = None) -> None:
        """Show the point cloud as a mesh with only vertices.
        Used for debug purpose.

        Keyword Arguments:
            vertices {Union[np.array, List[Vector]]} -- optional list of vertices to show (default: {None})
        """
        mesh = bpy.data.meshes.new("pc_vertices_data")
        obj = bpy.data.objects.new("pc_vertices", mesh)
        bpy.context.scene.collection.objects.link(obj)
        #
        vts = self.vertices if vertices is None else [tuple(v[0:3]) for v in vertices]
        mesh.from_pydata(vts, [], [])
        mesh.update()

    # ==============================================================================================
    def filter_point_cloud(self, target_pc_kdtree: KDTree, initial_alignment: Matrix,
                           distance_threshold: float) -> np.array:
        """Get a filtered version of the point cloud. The filtered cloud is also stored for later use.
        Optionally apply an initial alignment.

        Arguments:
            target_pc_kdtree {KDTree} -- KDTree of the point cloud to align to
            initial_alignment {Matrix} -- initial manual alignment, usually from the UI control empty
            distance_threshold {float} -- maximum allowed distance from ground truth

        Returns:
            np.array -- the filtered point cloud
        """
        logger.info("Starting reconstructed point cloud filtering")
        src = np.copy(self.vertices)
        #
        # initial alignment
        src = PointCloud.transform(src, initial_alignment)
        #
        # filter distant points
        self._discard_vertices.clear()
        self._filter_distance = distance_threshold
        to_delete = []
        for i, v in enumerate(src):
            if target_pc_kdtree.find(v)[2] > distance_threshold:
                to_delete.append(i)
        src = np.delete(src, to_delete, axis=0)
        self._discard_vertices = to_delete
        logger.info("Reconstructed points filtered. Discarded %i points!", len(to_delete))
        if src.shape[0] == 0:
            logger.warning("Point cloud contains 0 points!")
        return self.vertices_filtered

    # ==============================================================================================
    def get_regsitration_to_target(self, target_pc: List[Vector], initial_alignment: Matrix,
                                   target_pc_kdtree: KDTree = None,
                                   max_iterations: int = 100, samples: int = 0,
                                   use_filtered_cloud: bool = True) -> Tuple[Matrix, float]:
        """Get the registration matrix to a target point cloud. Optionally apply an initial alignment.
        Implements a variant of the Iterative Closest Point algorithm.

        Arguments:
            target_pc {List[Vector]} -- the point cloud to align to
            initial_alignment {Matrix} -- initial manual alignment, usually from the UI control empty

        Keyword Arguments:
            target_pc_kdtree {KDTree} -- KDTree of the point cloud to align to, if {None} will be
                                         created internally starting from `target_pc` (default: {None})
            max_iterations {int} -- maximum iterations allowed to the algorithm (default: {50})
            samples {int} -- number of random vertices to be used for alignment,
                             if <= 0 use the whole cloud (default: {0})
            use_filtered_cloud {bool} -- if {True} the filtered point cloud is used to run the alignment,
                                         otherwise the full cloud is used (default: {True})

        Returns:
            Matrix -- the combined transformation matrix to align the point cloud
            float  -- registration error
        """
        logger.info("Starting ICP, samples=%i, max_iterations=%i", samples, max_iterations)
        src_pc = self.vertices_filtered if use_filtered_cloud else self.vertices
        #
        target_pc = np.array(target_pc)
        src = np.ones((src_pc.shape[0], 4))
        target = np.ones((len(target_pc), 4))
        src[:, :3] = np.copy(src_pc)
        target[:, :3] = np.copy(target_pc)
        #
        # initial alignment
        src = PointCloud.transform(src, initial_alignment)
        #
        # build KDTree for target point cloud
        kdtree = target_pc_kdtree
        if kdtree is None:
            size = len(target_pc)
            kdtree = KDTree(size)
            for i, v in enumerate(target_pc):
                kdtree.insert(v, i)
            kdtree.balance()
        #
        # define samples
        if samples <= 0 or samples > src[:].shape[0]:
            logger.warning("Using %i points but were required %i!", src[:].shape[0], samples)
            samples = src[:].shape[0]
        #
        # randomize points
        indices = list(range(0, src[:].shape[0]))
        #
        current_iter = 0
        previous_error = float('inf')
        transforms = []
        while current_iter < max_iterations:
            shuffle(indices)
            s = list(zip(*[kdtree.find(src[i][0:3]) for i in indices[:samples]]))
            # s_vertices = s[0]
            s_indices = s[1]
            s_distances = s[2]
            #
            # get error
            mean_error = np.mean(s_distances)
            logger.info("ICP iteration %i, mean error: %f", current_iter, mean_error)
            if (previous_error - mean_error) < 0.0001:   # best alignment reached
                break
            previous_error = mean_error
            #
            # find fit transform
            T = self.find_fit_transform(src[indices[:len(s_indices)]], target[s_indices, :])
            transforms.append(T)
            #
            # update the current source cloud
            src = PointCloud.transform(src, T)
            #
            current_iter += 1
        #
        # self._show_as_vertices_mesh(src)
        align_matrix = Matrix(reduce(lambda am, t: t @ am, transforms).tolist())   # aggregate transformations
        return align_matrix, previous_error

    # ==============================================================================================
    @staticmethod
    def find_fit_transform(src: np.array, trg: np.array) -> np.matrix:
        """Find the best fit transformation between two point clouds.

        Arguments:
            src {np.array} -- source point cloud, to be aligned
            trg {np.array} -- target point cloud, to align to

        Returns:
            np.matrix -- best alignment transform matrix
        """
        d = src.shape[1]
        #
        # align centroids
        centroid_trg = np.mean(trg, axis=0)
        centroid_src = np.mean(src, axis=0)
        src_c = src - centroid_src
        trg_c = trg - centroid_trg
        #
        # compute rotation
        H = src_c.T @ trg_c
        u, _, vh = np.linalg.svd(H)
        R = vh.T @ u.T
        if np.linalg.det(R) < 0:
            vh[d-1, :] *= -1.
            R = vh.T @ u.T
        #
        # compute translation
        t = centroid_trg.T[0:3] - (R @ centroid_src.T)[0:3]
        #
        # build transformation matrix
        T = R
        T[:3, 3] = t
        return np.array(T)

    # ==============================================================================================
    @staticmethod
    def transform(vertices: np.array, m: Union[np.matrix, Matrix]) -> np.array:
        """Apply a tranformation matrix to the given vertices.

        Arguments:
            vertices {np.array} -- vertices to be transformed, can be either of 3D or 4D coordinates.
            m {Union[np.matrix, Matrix]} -- 4x4 transformation matrix

        Raises:
            ValueError: if the transformation matrix is not of shape 4x4

        Returns:
            np.array -- the transformed vertices, 3D or 4D based on the input `vertices`,
                        in the 4D case the coordinate is normalized and w=1
        """
        assert vertices.shape[1] == 3 or vertices.shape[1] == 4
        #
        if isinstance(m, Matrix):   # convert to numpy if needed
            m = np.array(m)
        if m.shape != (4, 4):
            raise ValueError("Transformation matrix must be of shape 4x4! (given {})".format(m.shape))
        if vertices.shape[1] == 3:
            src = np.ones((vertices.shape[0], 4))
            src[:, :3] = np.copy(vertices)
        else:
            src = np.copy(vertices)
        #
        for i, v in enumerate(src):
            v_new = m @ v
            src[i, :-1] = np.array([c / v_new[-1] for c in v_new[:-1]])   # x/w, y/w, z/w
            src[i, -1] = 1.
        #
        # self._show_as_vertices_mesh()
        if vertices.shape[1] == 3:
            return src[:, :-1]   # go back to 3D vectors
        return src               # keep 4D vectors

    # ==============================================================================================
    def evaluate(self, target_pc_kdtree: KDTree, use_filtered_cloud: bool) -> Dict:
        """Evaluate the point cloud w.r.t. the target point cloud.
        The evaluation is done in terms of euclidean distance between the clouds' points.

        Arguments:
            target_pc_kdtree {KDTree} -- target (ground truth) point cloud KDTree
            use_filtered_cloud {bool} -- if {True} the filtered cloud is used for evaluation, the full one otherwise

        Returns:
            Dict -- evaluation result dictionary containing:
                        'dist_mean' {float}: mean distance
                        'dist_std' {float}: standard deviation
                        'dist_min' {float}: minimum distance
                        'dist_max' {float}: maximum distance
                        'used_filtered_cloud' {bool}: if the evaluation used only the filtered cloud
                        'filter_threshold' {float}: the distance threshold used to filter the point cloud
                        'full_cloud_size' {int}: size of the whole reconstructed cloud
                        'used_cloud_size' {int}: size of the cloud used for the evaluation
                        'used_cloud_size_percent' {float}: percentage of cloud used for the evaluation (in range [0-1])
                        'discarded_points' {int}: number of point not used in the evaluation
                        'elapsed_time' {float}: elapsed time in seconds
                    note that the measure unit depends on the unit set in the scene.
        """
        src_pc = self.vertices_filtered if use_filtered_cloud else self.vertices
        #
        # initial alignment
        src = PointCloud.transform(src_pc, self._object_matrix @ self._initial_centroid_matrix)
        #
        # get distances
        d = [euclidean_distance(v, target_pc_kdtree.find(v)[0]) for v in src]  # no need to normalize points are 3D
        # d = [target_pc_kdtree.find(v)[2] for v in src]
        #
        # compute statistics
        d_mean = mean(d)
        d_std = stdev(d, d_mean) if len(d) > 1 else 0.
        d_min = min(d)
        d_max = max(d)
        #
        results = {
            "dist_mean": d_mean,
            "dist_std": d_std,
            "dist_min": d_min,
            "dist_max": d_max,
            "used_filtered_cloud": use_filtered_cloud,
            "filter_threshold": self._filter_distance if use_filtered_cloud else float('inf'),
            "full_cloud_size": len(self.vertices),
            "used_cloud_size": len(src),
            "used_cloud_size_percent": len(src) / len(self.vertices),
            "discarded_points": len(self.vertices) - len(src)
        }
        logger.debug("Point cloud eval end. mean=%.3f, std=%.3f, min=%.3f, max=%.3f.", d_mean, d_std, d_min, d_max)
        return results

    # ==============================================================================================
    def clear_filtered_cloud(self) -> None:
        """Clear the list of points that were discarded due to distance treshold filtering."""
        self._discard_vertices.clear()
        self._filter_distance = float('inf')

    # ==============================================================================================
    def has_filtered_cloud(self) -> bool:
        """Check if the point cloud has an active distance threshold filter.

        Returns:
            bool -- {True} if there is filtered, {False} otherwise
        """
        return (self._discard_vertices is not None) and (len(self._discard_vertices) != 0)

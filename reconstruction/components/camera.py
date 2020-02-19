
import logging
import re
from math import acos, degrees
from typing import Dict

import bpy
from gpu.types import GPUShader
from gpu_extras.batch import batch_for_shader
from mathutils import Matrix, Vector
from sfm_flow.utils import euclidean_distance
from sfm_flow.utils.camera import get_camera_lookat

logger = logging.getLogger(__name__)


class ReconCamera():
    """Representation of a reconstructed camera.

    Contains information about:
    - image filename
    - focal length
    - rotation
    - position
    - radial distortion
    """

    FRAME_NUMBER_REGEX = re.compile(r'.*?([0-9]+)(/undistorted)*\.[a-zA-Z]+$')

    # camera display symbol vertices
    SYMBOL_VERTICES = tuple(map(lambda v: Matrix.Scale(0.10, 3) @ v, (   # scale
        # position
        Vector((0, 0, 0)),
        # viewport
        Vector((-0.5, +0.28, -1.)), Vector((+0.5, +0.28, -1.)),
        Vector((+0.5, -0.28, -1.)), Vector((-0.5, -0.28, -1.)),
        # up direction
        Vector((-0.35, +0.33, -1.)), Vector((0, +0.7, -1.)), Vector((+0.35, +0.33, -1.))
    )))

    # camera display symbol lines indices
    SYMBOL_INDICES = (
        (1, 2), (2, 3), (3, 4), (4, 1),
        (0, 1), (0, 2), (0, 3), (0, 4),
        (5, 6), (6, 7), (7, 5)
    )

    # camera display symbol vertex shader
    _vertex_shader = '''
        in vec3 position;
        uniform mat4 perspective_matrix;
        uniform mat4 object_matrix;
        uniform mat4 initial_centroid_matrix;
        uniform vec3 color;
        out vec4 f_color;
        void main() {
            gl_Position = perspective_matrix * object_matrix * initial_centroid_matrix * vec4(position, 1.0f);
            f_color = vec4(color[0], color[1], color[2], 1.0f);
        }
    '''

    # camera display symbol fragment shader
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
    def matrix_world(self) -> Matrix:
        """Worldspace transformation matrix."""
        return self._object_matrix @ self._initial_centroid_matrix @ self._recon_matrix_world

    # ==============================================================================================
    @property
    def position(self) -> Vector:
        """The camera position."""
        return self.matrix_world.to_translation()

    # ==============================================================================================
    @property
    def rotation(self) -> Vector:
        """The camera rotation quaternion."""
        return self.matrix_world.to_quaternion()

    # ==============================================================================================
    @property
    def scale(self) -> Vector:
        """The camera scale."""
        return self.matrix_world.to_scale()

    # ==============================================================================================
    @property
    def look_at(self) -> Vector:
        """The camera look at direction Vector."""
        return self.rotation @ Vector((0.0, 0.0, -1.0))

    ################################################################################################
    # Constructor
    #

    def __init__(self, filename: str, focal_length: float, matrix_world: Matrix, radial_distortion: float):
        """Initialize a reconstructed camera.
        Contains information about: image filename, focal length, rotation, position, and radial distortion


        Arguments:
            filename {str} -- filename of the associated image
            focal_length {float} -- focal length in millimeters
            matrix_world {Matrix} -- 4x4 world transformation matrix
            radial_distortion {float} -- radial distortion factor
        """
        self.filename = filename
        self.frame_number = int(ReconCamera.FRAME_NUMBER_REGEX.match(self.filename).group(1))
        self.focal_length = focal_length
        self.radial_distortion = radial_distortion
        self._recon_matrix_world = matrix_world

        # point cloud object matrix, to be set to UI control element world_matrix
        self._object_matrix = None

        # initial centroid translation matrix
        self._initial_centroid_matrix = None

        self._shader = None
        self._batch = None

        user_preferences = bpy.context.preferences
        addon_user_preferences_name = (__name__)[:__name__.index('.')]
        self._cam_color = user_preferences.addons[addon_user_preferences_name].preferences.recon_camera_color
        # NOTE: when running in dev mode the color reference is lost on add-on reload (the color becomes random).
        # A possible solution is to create a copy but then i will loose the ability to change the color
        # of existing reconstructions from the preferences dialog.

    ################################################################################################
    # Methods
    #

    # ==============================================================================================
    def show(self, object_matrix: Matrix, initial_centroid_matrix: Matrix) -> None:
        """Setup shaders and other required data to show the refconstructed cameras.

        Arguments:
            object_matrix {bpy.types.Object} -- user interface handle object matrix
            initial_centroid_matrix {Matrix} -- initial centroid matrix of the recontruction
        """
        pos = list(map(lambda v: self._recon_matrix_world @ v, ReconCamera.SYMBOL_VERTICES))
        # setup shader
        self._shader = GPUShader(ReconCamera._vertex_shader, ReconCamera._fragment_shader)
        self._batch = batch_for_shader(self._shader, 'LINES', {"position": pos}, indices=ReconCamera.SYMBOL_INDICES)
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
        self._shader.uniform_float("color", self._cam_color)

    # ==============================================================================================
    def evaluate(self, scene: bpy.types.Scene) -> Dict:
        """Given a scene evaluate the camera pose w.r.t. the ground truth.

        Arguments:
            scene {scene} -- scene, includes the render camera that will be used as ground truth

        Returns:
            Dict -- evaluation result dictionary containing:
                        'position_distance' {float}: position distance (measure unit depends on the scene's unit)
                        'lookat_difference_rad' {float}: non-oriented angle between lookAt vectors, in radians
                        'lookat_difference_deg' {float}: non-oriented angle between lookAt vectors, in degrees
                        'rotation_difference_rad' {float}: angle to align reconstructed camera to gt, in radians
                        'rotation_difference_deg' {float}: angle to align reconstructed camera to gt, in degrees
        """
        # get ground truth
        scene.frame_set(self.frame_number)
        gt_matrix_world = scene.camera.matrix_world
        gt_pos = gt_matrix_world.to_translation()
        gt_rotation = gt_matrix_world.to_quaternion()
        gt_lookat = get_camera_lookat(scene.camera)
        #
        # --- position evaluation
        pos_distance = euclidean_distance(gt_pos, self.position)
        logger.debug("Camera position distance: %f (GT=%s, recon=%s)", pos_distance, gt_pos, self.position)
        #
        # --- look-at evaluation
        # compute the non-oriented angle between look-at vectors (gt and reconstructed)
        cos_theta = (gt_lookat @ self.look_at) / (gt_lookat.length * self.look_at.length)
        if cos_theta > 1.0 and cos_theta < 1.1:  # rounding error
            cos_theta = 1.0
        theta_rad = acos(cos_theta)
        theta_deg = degrees(theta_rad)
        logger.debug("Camera look-at: %f deg, %f rad. (GT=%s, recon=%s)", theta_deg, theta_rad, gt_lookat, self.look_at)
        #
        # --- rotation evaluation
        # compute rotation angle to align reconstructed camera to gt
        rot_diff = self.rotation.conjugated() @ gt_rotation
        #rot_diff = self.rotation.rotation_difference(gt_rotation)
        rot_diff_rad = rot_diff.angle
        rot_diff_deg = degrees(rot_diff_rad)
        if rot_diff_deg > 180.0:  # angle in range 0-360, equal to +0-180 or -0-180
            rot_diff_deg = 360.0 - rot_diff_deg
        logger.debug("Camera rotation difference: %f deg (GT=%s, recon=%s)", rot_diff_deg, gt_rotation, self.rotation)
        #
        results = {
            "position_distance": pos_distance,
            "lookat_difference_rad": theta_rad,
            "lookat_difference_deg": theta_deg,
            "rotation_difference_rad": rot_diff_rad,
            "rotation_difference_deg": rot_diff_deg
        }
        return results

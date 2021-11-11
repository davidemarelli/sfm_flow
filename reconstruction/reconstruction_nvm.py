
import logging
from math import pi
from typing import List

from mathutils import Color, Matrix, Quaternion, Vector
from sfm_flow.reconstruction.components import PointCloud, ReconCamera, ReconModel
from sfm_flow.reconstruction.reconstruction_base import ReconstructionBase

logger = logging.getLogger(__name__)


class ReconstructionNvm(ReconstructionBase):
    """The actual SfM reconstruction imported from an NVM file.

    http://ccwu.me/vsfm/index.html
    File format: http://ccwu.me/vsfm/doc.html#nvm
    """

    SUPPORTED_EXTENSION = ".nvm"

    # coordinates conversion matrix, from canonical right handed (Y-up) to blender's (Z-up)
    NVM_TO_BLENDER = Matrix.Rotation(-pi / 2, 4, 'X')

    ################################################################################################
    # Constructor and destructor
    #

    # ==============================================================================================
    def __init__(self, name: str, nvm_file_path: str):
        """Create a reconstruction object and load the reconstruction from the N-View Match file.

        Arguments:
            name {str} -- reconstruction name
            file_path {str} -- path to the NVM reconstruction file
        """
        super().__init__(name)
        #
        self.file_path = nvm_file_path
        self.file = open(self.file_path, "r")
        self.file.seek(0, 2)
        self.file_end = self.file.tell()  # get char count
        self.file.seek(0)
        #
        self._load_reconstruction()

    # ==============================================================================================
    def __del__(self):
        """Ensure file release on object deletion."""
        if hasattr(self, "file"):
            self.close()
        super().__del__()

    # ==============================================================================================
    def close(self) -> None:
        """Close the NVM file if necessary.
        This is called by '__del__' to enure proper resource release.
        """
        if self.file:
            self.file.close()

    ################################################################################################
    # Helpers
    #

    # ==============================================================================================
    def _load_reconstruction(self) -> None:
        """Read the content of an NVM reconstruction file and populate data structures.

        Raises:
            ValueError: if something goes wrong reading the NVM file (eg. unexpected header, wrong cameras
                        or points, wrong PLY count).
                        Other errors are raised if there are errors in the NVM file structure or file access.
        """
        # read file header
        header = self._read_line()[0]
        if header != "NVM_V3":
            msg = f"Unexpected header '{header}' (expected 'NVM_V3')"
            logger.error(msg)
            raise ValueError(msg)
        calibration = None
        if isinstance(header, list) and len(header) == 6:   # calibration params are present
            calibration = list(map(float, header[1:]))
        self.calibration = calibration
        #
        # read models and ply sections
        self._read_models()
        if self.file.tell() < self.file_end:   # avoid if already reached EOF
            self._read_ply_files()
        #
        # close, everything has been read
        self.close()

    # ==============================================================================================
    def _read_models(self) -> None:
        """Read the 'models' section of the nvm file, populate self.models

        Raises:
            ValueError: If errors in the nvm file (i.e. wrong camera or point count)
        """
        model_index = 0
        camera_count = -1
        while camera_count != 0:
            #
            # --- read cameras
            try:
                camera_count = int(self._read_line()[0])
            except EOFError:
                # handle COLMAP NVM files that do not use '0' to end the models section
                logger.warning("NVM file ended without model section termination character!")
                camera_count = 0
            #
            if camera_count != 0:   # not end of model section
                model = ReconModel(self.name + '_' + str(model_index))
                model.number_of_cameras = camera_count
                #
                for _ in range(0, camera_count):
                    camera_entry = self._read_line()
                    ReconstructionNvm._add_camera_from_nvm_entry(model, camera_entry)
                #
                # --- read points
                point_count = int(self._read_line()[0])
                pc = PointCloud(point_count)
                for _ in range(0, point_count):
                    point_entry = self._read_line()
                    ReconstructionNvm._add_point_from_nvm_entry(pc, point_entry)
                model.point_cloud = pc
                #
                self.add_model(model)

    # ==============================================================================================
    def _read_ply_files(self) -> None:
        """Read PLY secion of the NVM file.

        Raises:
            ValueError: if declared PLY count differs from count of models with PLY file
        """
        ply_count = int(self._read_line()[0])
        if ply_count != 0:
            ply_indices = list(map(int, self._read_line()))
            if len(ply_indices) == ply_count:
                for i in ply_indices:
                    self.models[i].has_ply_file = True
            else:
                msg = "Declared PLY files count ({}) is not equal to models with PLY file ({})!".format_map(
                    ply_count, len(ply_indices))
                logger.error(msg)
                raise ValueError(msg)

    # ==============================================================================================
    def _read_line(self) -> List[str]:
        """Read a line from the NVM file. Automatically discard empty lines and comments.

        Returns:
            List[str] -- the list of string tokens in the line

        Raises:
            EOFError: if reading lines after end of file
        """
        while True:
            line = self.file.readline().strip()
            if line == '' and self.file.tell() >= self.file_end:
                raise EOFError("Reading after file end!")
            elif line != '' and not line.startswith('#'):   # skip empty lines and comments
                return line.split()

    # ==============================================================================================
    @staticmethod
    def _add_camera_from_nvm_entry(model: ReconModel, args: List[str]) -> ReconCamera:
        """Init a reconstructed camera given a camera string from an NVM file.
        Adds the camera to the reconstructed model.

        Arguments:
            model {ReconModel} -- 3D reconstruction model
            args {List[str]} -- List of camera parameters, length must be 11.
                                Args ids and format:
                                    <filename>: str,
                                    <focal length>: float,
                                    <quaternion WXYZ>: 4x float,
                                    <camera center XYZ>: 3x float,
                                    <radial distortion>: float,
                                    0

        Returns:
            ReconCamera -- reconstructed camera imported from file
        """
        assert len(args) == 11 and (args[10] == '0' or args[10] == 0)
        #
        filename = args[0].replace("\"", " ")           # type: str
        focal_length = float(args[1])                   # type: float
        radial_distortion = float(args[9])              # type: float

        # get rotation and translation
        q = Quaternion(map(float, args[2:6]))   # rotation quaternion
        c = Vector(map(float, args[6:9]))       # camera center
        rotation = q.to_matrix()
        t = - (rotation @ c)                    # translation = - R * C

        # build matrix world
        w2c = rotation.to_4x4()
        w2c[0][3] = t.x
        w2c[1][3] = t.y
        w2c[2][3] = t.z
        w2c = Matrix.Rotation(pi, 4, 'X') @ w2c  # move to canonical right handed (Y-up)
        matrix_world = ReconstructionNvm.NVM_TO_BLENDER @ w2c.inverted()  # move to blender global (Z-up)

        cam = ReconCamera(filename, focal_length, matrix_world, radial_distortion)
        model.add_camera(cam)
        return cam

    # ==============================================================================================
    @staticmethod
    def _add_point_from_nvm_entry(point_cloud: PointCloud, args: List[str]) -> None:
        """Set a point of the cloud given the list of strings from the NVM file entry.
        Adds the point to the point cloud.

        Arguments:
            args {List[str]} -- List[<XYZ> <RBG> <number of measurements> List[<image index> <feature Index> <xy>]]

        Raises:
            RuntimeError: if called when trying to set more points than the cloud size
        """
        assert len(args) >= 7 and (len(args) == (7 + 4*int(args[6])))

        # load vertex coordinates
        position = ReconstructionNvm.NVM_TO_BLENDER @ Vector(map(float, args[0:3]))
        #
        # load colors
        color = Color(map(int, args[3:6])) / 255.
        #
        # load measures
        # self.number_of_measures = int(args[6])
        # self.measures = []
        # for offset in range(self.number_of_measures):
        #     start_index = 7 + offset*4
        #     self.measures.append(ReconMeasure(args[start_index:start_index+4]))
        #
        point_cloud.add_point(position, color)


import logging
import os
import re
from math import pi
from typing import List

from mathutils import Color, Matrix, Vector
from sfm_flow.reconstruction.components import PointCloud, ReconCamera, ReconModel
from sfm_flow.reconstruction.reconstruction_base import ReconstructionBase

logger = logging.getLogger(__name__)


class ReconstructionBundle(ReconstructionBase):
    """The actual SfM reconstruction imported form a Bundle file.

    https://www.cs.cornell.edu/~snavely/bundler/
    File format: https://www.cs.cornell.edu/~snavely/bundler/bundler-v0.4-manual.html#S6
    """

    SUPPORTED_EXTENSION = ".rd.out"

    # coordinates conversion matrix, from canonical right handed (Y-up) to blender's (Z-up)
    BUNDLE_TO_BLENDER = Matrix.Rotation(-pi / 2, 4, 'X')

    LIST_FILE_REGEX = re.compile(r'(.*?[0-9]+\.[a-zA-Z]+)(\s|$)')

    ################################################################################################
    # Constructor and destructor
    #

    # ==============================================================================================
    def __init__(self, name: str, bundle_file_path: str):
        """Create a reconstruction object and load the reconstruction from the Bundle file.

        Arguments:
            name {str} -- reconstruction name
            file_path {str} -- path to the bundle.rd.out reconstruction file
        """
        super().__init__(name)
        #
        self.file_path = os.path.abspath(bundle_file_path)
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
        """Close the Bundle file if necessary.
        This is called by '__del__' to enure proper resource release.
        """
        if self.file:
            self.file.close()

    ################################################################################################
    # Helpers
    #

    # ==============================================================================================
    def _load_reconstruction(self) -> None:
        """Read the content of an Bundle reconstruction file and populate data structures.

        File format: https://www.cs.cornell.edu/~snavely/bundler/bundler-v0.4-manual.html

        Raises:
            ValueError: if something goes wrong reading the Bundle file (unexpected header, wrong cameras or points).
                        Other errors are raised if there are errors in the Bundle file structure or file access.
        """
        cam_name_list = self._load_camera_list()
        # read file header
        header = self.file.readline().strip()
        if header != "# Bundle file v0.3":
            msg = f"Unexpected header '{header}' (expected '# Bundle file v0.3')"
            logger.error(msg)
            raise ValueError(msg)
        #
        # get quantity of available cameras and points in file
        l = self._read_line()
        camera_count = int(l[0])
        point_count = int(l[1])
        assert camera_count == len(cam_name_list)   # the amount of cameras must match across files
        #
        model = ReconModel(self.name + '_0')
        model.number_of_cameras = camera_count
        #
        # load reconstructed camera poses
        for i in range(0, camera_count):
            #
            # <f> <k1> <k2>   [focal length follwed by 2 radial distortion coefficients]
            f_k1_k2 = self._read_line()
            #
            # <R>             [3x3 matrix, camera rotation]
            r = Matrix.Identity(3)
            for row in range(3):
                r[row] = list(map(float, self._read_line()))
            #
            # <t>             [XYZ vector, camera translation]
            t = Vector(list(map(float, self._read_line())))
            #
            # build world matrix
            w2c = r.to_4x4()
            w2c[0][3] = t.x
            w2c[1][3] = t.y
            w2c[2][3] = t.z
            c2w = w2c.inverted()
            c2w = ReconstructionBundle.BUNDLE_TO_BLENDER @ c2w
            #
            model.add_camera(ReconCamera(cam_name_list[i], float(f_k1_k2[0]), c2w, list(map(float, f_k1_k2[1:2]))))
        #
        # load reconstructed point cloud
        pc = PointCloud(point_count)
        for i in range(0, point_count):
            #
            # <position>      [a 3-vector describing the 3D position of the point]
            p = ReconstructionBundle.BUNDLE_TO_BLENDER @ Vector(list(map(float, self._read_line())))
            #
            # <color>         [a 3-vector describing the RGB color of the point]
            c = Color(list(map(int, self._read_line()))) / 255.
            #
            # <view list>     [a list of views the point is visible in]
            self._read_line()  # currently unused
            #
            pc.add_point(p, c)
        #
        model.point_cloud = pc
        self.add_model(model)
        #
        # close, everything has been read
        self.close()

    # ==============================================================================================
    def _load_camera_list(self) -> List[str]:
        """Load the camera list file names in the same order of appearance in the bundle.rd.out file.

        Raises:
            FileNotFoundError: if bundle.rd.out.list.txt OR list.txt are missing

        Returns:
            List[str] -- list of file names
        """
        files_dir = os.path.dirname(self.file_path)
        f_names = []
        #
        # handle VisualSfM special case, images are renamed during export for PMVS.
        # in this case original images names (frame numbers) can be found in
        # "cameras_v2.txt" instead of "bundle.rd.out.list.txt"
        camera_list_filename = os.path.join(files_dir, "cameras_v2.txt")
        if os.path.isfile(camera_list_filename):  # if file exists assume is a VisualSfM reconstruction
            with open(camera_list_filename, "r") as f:
                #
                # check header
                header = f.readline().strip()
                if not header == "# Camera parameter file.":
                    raise ValueError("Wrong file format (" + header + ") for VisualSfM \"cameras_v2.txt\"")
                logger.info("Found VisualSfM cameras v2 file")
                for _ in range(15):
                    f.readline()  # discard header
                #
                # get camera quantity
                cam_count = int(f.readline().strip())
                #
                # load frame numbers form file
                for _ in range(cam_count):
                    while f.readline() != "\n":   # discard unused data
                        pass
                    f.readline()                  # discard first line (new filename)
                    #
                    f_names.append(f.readline())  # get original image path
        #
        #
        # back to normal case
        else:
            cameraListFileName = os.path.join(files_dir, "bundle.rd.out.list.txt")
            if not os.path.isfile(cameraListFileName):
                cameraListFileName = os.path.join(files_dir, "list.txt")
                if not os.path.isfile(cameraListFileName):
                    raise FileNotFoundError("Could not find bundle.rd.out.list.txt OR list.txt")
            #
            with open(cameraListFileName, "r") as f:
                for _, line in enumerate(iter(f.readline, '')):
                    filename = ReconstructionBundle.LIST_FILE_REGEX.match(line)
                    filename = filename.group(1)
                    f_names.append(filename)
        #
        return f_names

    # ==============================================================================================
    def _read_line(self) -> List[str]:
        """Read a line from the bundle file. Automatically discard empty lines and comments.

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

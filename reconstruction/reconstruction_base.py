
import logging
from abc import ABCMeta, abstractmethod
from typing import Dict, List

import bpy

from .components import ReconModel

logger = logging.getLogger(__name__)


class ReconstructionBase(metaclass=ABCMeta):
    """The actual 3D reconstruction.
    Contains information on the reconstructed models (ideally one only) and the functions to render them in the 3D view.

    This base class can be extended to provide support to import multiple reconstructions format.
    See {sfm_flow.reconstruction.ReconstructionNvm} and {sfm_flow.reconstruction.ReconstructionBundle} for examples.
    Sub-classes placed in this folder will be auto-discovered and loaded by the add-on.
    """

    # ==============================================================================================
    # Dictionary mapping files extensions to importers, see get_supported_files
    _importer_map = None   # type: Dict

    # ==============================================================================================
    @property
    @classmethod
    @abstractmethod
    def SUPPORTED_EXTENSION(cls) -> str:
        """Extension supported by the sub-class. Must be defined by all the sub-classes!
        https://stackoverflow.com/a/53417582

        Returns:
            str -- file extension
        """
        return NotImplementedError

    ################################################################################################
    # Constructor and destructor
    #

    # ==============================================================================================
    def __init__(self, name: str):
        """Create a new 3D reconstruction object.

        Arguments:
            name {str} -- reconstruction name
        """
        self.name = name          # type: str

        # Camera calibration [ FixedK fx cx fy cy ]
        self.calibration = None   # type: List[float]

        # List of reconstructed 3D models
        self.models = []          # type: List[ReconModel]

    # ==============================================================================================
    def __del__(self):
        """Remove reconstruction models on object deletion."""
        if hasattr(self, "models"):
            self.free()
            del self.models

    # ==============================================================================================
    def free(self) -> None:
        """Release resources claimed by reconstruction's models"""
        for m in self.models:
            m.free()

    ################################################################################################
    # Methods
    #

    # ==============================================================================================
    def select_set(self, state: bool) -> None:
        """Select/deselect all the models in the reconstruction.

        Arguments:
            state {bool} -- Selected if {True}, deselected otherwise
        """
        for m in self.models:
            m.select_set(state)

    # ==============================================================================================
    def add_model(self, model: ReconModel) -> None:
        """Append a model to the 3D reconstruction.

        Arguments:
            model {ReconModel} -- reconstructed model
        """
        self.models.append(model)

    # ==============================================================================================
    def show(self) -> None:
        """Show the reconstructed 3D models in Blender's 3D view."""
        for m in self.models:
            m.show()
        bpy.ops.object.select_all(action='DESELECT')
        self.select_set(True)

    # ==============================================================================================
    def unload_deleted(self) -> bool:
        """Unload deleted models, the reconstruction models that are flagged with 'is_removed'.

        Returns:
            bool -- {True} if the reconstruction is empty (has no models left), {False} otherwise
        """
        to_delete = [model for model in self.models if model.is_removed is True]
        for model in to_delete:
            logger.debug("Removing model '%s' from reconstruction '%s'", model.name, self.name)
            del self.models[self.models.index(model)]
        return len(self.models) == 0

    ################################################################################################
    # Static methods
    #

    # ==============================================================================================
    @staticmethod
    def get_supported_files() -> Dict:
        """Get a dictionary mapping the supported reconstruction extensions to the correct importer.

        Returns:
            Dict -- key=extension, value=importerClass
        """
        if ReconstructionBase._importer_map is not None:
            return ReconstructionBase._importer_map
        #
        i_map = {}
        for c in ReconstructionBase.__subclasses__():
            i_map[c.SUPPORTED_EXTENSION] = c
        ReconstructionBase._importer_map = i_map
        return i_map

    # ==============================================================================================
    @staticmethod
    def get_supported_files_filter() -> str:
        """Get the supported files filter string for the file selection dialog.

        Returns:
            str -- glob filter string
        """
        f = None
        for k in ReconstructionBase.get_supported_files():
            if f is None:
                f = f"*{k}"
            else:
                f += f";*{k}"
        return f

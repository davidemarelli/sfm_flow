
from ..reconstruction.properties import SFMFLOW_ReconstructionModelProperties
from ..utils import register_classes as _register_classes
from ..utils import unregister_classes as _unregister_classes
from .preferences import AddonPreferences
from .properties import SFMFLOW_AddonProperties

####################################################################################################
# Register and unregister
#

_CLASSES = (
    SFMFLOW_AddonProperties,
    SFMFLOW_ReconstructionModelProperties,
)


# ==================================================================================================
def properties_register() -> None:
    """Register additional ui panels."""
    _register_classes(_CLASSES)


# ==================================================================================================
def properties_unregister() -> None:
    """Unregister additional ui panels."""
    _unregister_classes(_CLASSES)

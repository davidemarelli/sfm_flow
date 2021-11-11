
from ...utils import register_classes as _register_classes
from ...utils import unregister_classes as _unregister_classes
from .render_cameras import RENDERCAMERA_UL_property_list_item

####################################################################################################
# Register and unregister
#


_CLASSES = (
    RENDERCAMERA_UL_property_list_item,
)


# ==================================================================================================
def components_register() -> None:
    """Register additional ui components."""
    _register_classes(_CLASSES)


# ==================================================================================================
def components_unregister() -> None:
    """Unregister additional ui components."""
    _unregister_classes(_CLASSES)

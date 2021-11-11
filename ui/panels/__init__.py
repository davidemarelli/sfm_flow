
from sfm_flow.utils import register_classes as _register_classes
from sfm_flow.utils import unregister_classes as _unregister_classes

from .pipelines_panel import SFMFLOW_PT_pipelines_tools
from .render_panel import SFMFLOW_PT_render_tools
from .root_panel import SFMFLOW_PT_main

####################################################################################################
# Register and unregister
#

_CLASSES = (
    SFMFLOW_PT_main,
    SFMFLOW_PT_render_tools,
    SFMFLOW_PT_pipelines_tools,
)


# ==================================================================================================
def panels_register() -> None:
    """Register additional ui panels."""
    _register_classes(_CLASSES)


# ==================================================================================================
def panels_unregister() -> None:
    """Unregister additional ui panels."""
    _unregister_classes(_CLASSES)

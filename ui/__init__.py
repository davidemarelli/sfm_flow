
from .components import components_register, components_unregister
from .menus import menu_register, menu_unregister
from .panels import (SFMFLOW_PT_main, SFMFLOW_PT_pipelines_tools, SFMFLOW_PT_render_tools,
                     panels_register, panels_unregister)

####################################################################################################
# Register and unregister
#


# ==================================================================================================
def ui_register() -> None:
    """Register ui elements."""
    components_register()
    menu_register()
    panels_register()


# ==================================================================================================
def ui_unregister() -> None:
    """Unregister ui elements."""
    panels_unregister()
    menu_unregister()
    components_unregister()

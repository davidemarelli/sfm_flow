"""
***************************************************************************************************
* SfM Flow
*
* University of Milano - Bicocca
* DISCo - Department of Informatics, Systems and Communication
* Imaging and Vision Laboratory (IVL)
* Viale Sarca 336, 20126 Milano, Italy
*
* Copyright © 2020 by:
*   Davide Marelli   - davide.marelli@unimib.it
*   Simone Bianco    - simone.bianco@unimib.it
*   Gianluigi Ciocca - gianluigi.ciocca@unimib.it
*
* Released under the MIT License terms
***************************************************************************************************

See the wiki for details. https://github.com/davidemarelli/sfm_flow/wiki

REQUIREMENTS:
  - Blender v2.80.75+ with Cycles
  - ExifTool (tested with v10.67), configure path in add-on's preferences

NOTES:
  - tested on Ubuntu 18.04 LTS and Windows 10 x64 with Blender v2.80.75
  - once installed all controls are available in Blender's `Properties -> Scene -> SfM Flow`
  - log is printed on console:
    - Windows: menu `Window -> Toggle System Console`
    - Linux: run Blender from terminal
"""

import logging

import bpy

import sfm_flow.utils.logutils as logutils
from sfm_flow.utils.callbacks import Callbacks

from .operators import SFMFLOW_OT_render_images, operators_register, operators_unregister
from .prefs import properties_register, properties_unregister
from .prefs.preferences import AddonPreferences, preferences_register, preferences_unregister
from .ui import ui_register, ui_unregister

####################################################################################################
# Addon globals
#

bl_info = {   # pylint: disable=invalid-name
    "name": "SfM Flow",
    "description": "Structure-from-Motion tools for synthetic dataset generation and 3D reconstruction evaluation.",
    "author": "Davide Marelli, Simone Bianco, Gianluigi Ciocca",
    "version": (1, 0, 2),
    "blender": (2, 80, 75),
    "location": "Properties > Scene > SfM Flow",
    "wiki_url": "https://github.com/davidemarelli/sfm_flow/wiki",
    "category": "3D Reconstruction"
}


####################################################################################################
# Add-on enable/disable
#

# ==================================================================================================
def register() -> None:
    """Register SfM Flow functionalities"""
    # load preferences
    preferences_register()
    prefs = bpy.context.preferences.addons[__name__].preferences   # type: AddonPreferences

    # setup logging
    log_level = int(prefs.log_level)
    logutils.setup_logger(log_level=log_level)
    logger = logging.getLogger(__name__)

    # properties, operators, ui
    properties_register()
    operators_register()
    ui_register()

    # handlers
    bpy.app.handlers.render_write.append(SFMFLOW_OT_render_images.render_complete_callback)
    bpy.app.handlers.depsgraph_update_post.append(Callbacks.cam_pose_update)
    bpy.app.handlers.save_post.append(Callbacks.post_save)
    bpy.app.handlers.load_post.append(Callbacks.post_load)

    logger.info("SFM Flow initialization complete!")


# ==================================================================================================
def unregister() -> None:
    """Un-register SfM Flow functionalities."""
    logger = logging.getLogger(__name__)

    # handlers
    bpy.app.handlers.render_write.remove(SFMFLOW_OT_render_images.render_complete_callback)
    bpy.app.handlers.depsgraph_update_post.remove(Callbacks.cam_pose_update)
    bpy.app.handlers.save_post.remove(Callbacks.post_save)
    bpy.app.handlers.load_post.remove(Callbacks.post_load)

    # ui, operators, preferences, properties
    ui_unregister()
    operators_unregister()
    preferences_unregister()
    properties_unregister()

    logger.info("SFM Flow unload complete!")

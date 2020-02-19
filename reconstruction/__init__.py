"""Reconstruction import, rendering, and evaluation.

Automatically discovers and import extensions of the ReconstructionBase class.
"""

import os
import sys
from importlib import util

from .manager import ReconstructionsManager
from .properties import SFMFLOW_ReconstructionModelProperties
from .reconstruction_base import ReconstructionBase

#from .reconstruction_bundle import ReconstructionBundle
#from .reconstruction_nvm import ReconstructionNvm

# dynamic import of all the available reconstruction loaders
excluded_files = (   # pylint: disable=invalid-name
    '__init__.py',
    'reconstruction_base.py',
    'manager.py',
    'properties.py'
)
current_dir = os.path.dirname(__file__)   # pylint: disable=invalid-name
for module_file in [f for f in os.listdir(current_dir) if os.path.isfile(os.path.join(current_dir, f))]:
    if module_file in excluded_files or module_file[-3:] != '.py':
        continue
    module_name = module_file[:-3]
    spec = util.spec_from_file_location(module_name, os.path.join(os.path.dirname(__file__), module_file))
    module = util.module_from_spec(spec)
    sys.modules[__name__+module_name] = module
    # FIXME allow relative imports in loaders
    # parent_module = sys.modules[__name__]
    # setattr(parent_module, module_name, module)
    #
    spec.loader.exec_module(module)

del current_dir

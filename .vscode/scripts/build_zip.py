"""Utility to build the addon's zip file."""

import os
import re
import zipfile
from datetime import datetime
from typing import Dict

####################################################################################################
# Exclude folders and files
#

EXCLUDE_DIRS = (
    # directories excluded form zip as regex
    r"\.",           # all .xxx folders
    r"__pycache__",  # cache folders
    r"build"
)

EXCLUDE_FILES = (
    # files excluded form zip as regex
    r"\.",         # all .xxx files
    r".*\.pyc$",   # cache files
    r"requirements.txt"
)


####################################################################################################
# Load addon informations

def load_addon_infos() -> Dict:
    """Load the addon `bl_info` dictionary directly from the addon __init__.py file.

    Raises:
        EnvironmentError: if the dictionary is not defined in __init__.py

    Returns:
        Dict -- bl_info, @see https://wiki.blender.org/wiki/Process/Addons/Guidelines/metainfo
    """
    addon_init = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../../__init__.py")
    addon_infos = {}   # pylint: disable=redefined-outer-name
    with open(addon_init, 'r') as f:
        s = f.read()
        d = re.search(r'bl_info = \{[^\}]*\}', s)
        if d is None:
            raise EnvironmentError("Cannot load the addon information dictionary!")
        g = d.group(0)
        exec(g, addon_infos)   # pylint: disable=exec-used
        addon_infos = addon_infos["bl_info"]
    return addon_infos


####################################################################################################
# Build zip

if __name__ == '__main__':
    # pylint: disable=invalid-name
    print("\nRecovering addon infos...")
    addon_infos = load_addon_infos()
    #
    cur_dir = os.path.abspath(os.path.dirname(__file__))
    addon_dir = os.path.normpath(os.path.join(cur_dir, "../../"))
    build_dir = os.path.join(addon_dir, "build/")
    os.makedirs(build_dir, exist_ok=True)
    addon_name = addon_infos["name"].replace(' ', '-')
    addon_ver = '.'.join(str(v) for v in addon_infos["version"])
    build_date = datetime.today().strftime('%y%m%d')
    zipname = addon_name + "_v" + addon_ver + "_" + build_date + ".zip"
    zip_filepath = os.path.join(build_dir, zipname)
    #
    print("Directory: " + addon_dir)
    print("Name: " + addon_name)
    print("Version: " + addon_ver)
    print("Build date: " + build_date)
    print("Zip output: " + zip_filepath)
    #
    with zipfile.ZipFile(zip_filepath, mode='w', compression=zipfile.ZIP_DEFLATED, allowZip64=False) as zf:
        print("\nBuilding addon zip...")
        #
        filecount = 0
        for root, dirs, files in os.walk(addon_dir):
            # filter excluded dirs and files
            dirs[:] = [d for d in dirs if not any([re.match(p, d) for p in EXCLUDE_DIRS])]
            files[:] = [f for f in files if not any([re.match(p, f) for p in EXCLUDE_FILES])]
            # add files to zip
            for file in files:
                filepath = os.path.join(root, file)
                path = os.path.relpath(filepath, addon_dir)
                arcname = os.path.join("sfm_flow/", path)
                zf.write(filepath, arcname=arcname)
                print("\t" + arcname)
                filecount += 1
    #
    print("\n{} files were added to zip '{}'".format(filecount, zip_filepath))

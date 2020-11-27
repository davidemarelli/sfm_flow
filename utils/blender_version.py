
from enum import Enum


class BlenderVersion(tuple, Enum):
    """Enumeration of the bender versions.

    Version comparison can use standard comparison operators, for example:
        bpy.app.version >= BlenderVersion.V2_82
    BE CAREFUL, use `==` and `!=` to deal with patch-specific problems only.

    Blender version is defined in the source code file 'source/blender/blenkernel/BKE_blender_version.h' by:
        - BLENDER_VERSION -- major and minor versions (eg. 283 is version 2.83.x)
        - BLENDER_SUBVERSION -- patch version (till version 2.82.x, from 2.83.x is replaced by BLENDER_VERSION_PATCH)
        - BLENDER_VERSION_PATCH -- patch version (starting from version 2.83.x)
        - BLENDER_VERSION_CHAR -- patch version as a character, same as BLENDER_SUBVERSION but uses a
                                  character (eg. 2.82a). Used till version 2.82.x

    Here the release notes: https://wiki.blender.org/wiki/Reference/Release_Notes
    """
    #
    # --- v2.80
    V2_80 = (2, 80, 0)
    V2_80_0 = (2, 80, 0)
    V2_80_74 = (2, 80, 74)   # 2.80-rc1 and rc2
    V2_80_75 = (2, 80, 75)   # 2.80-rc3 and 2.80 - July 29, 2019
    #
    # --- v2.81
    V2_81 = (2, 81, 0)       # 2.81  - November 21, 2019
    V2_81_0 = (2, 81, 0)
    V2_81_16 = (2, 81, 16)   # 2.81a - December 5, 2019
    V2_81a = (2, 81, 16)
    #
    # --- v2.82
    V2_82 = (2, 82, 0)       # 2.82  - February 14, 2020
    V2_82_0 = (2, 82, 0)
    V2_82_7 = (2, 82, 7)     # 2.82a - March 12, 2020
    V2_82a = (2, 82, 7)
    #
    # --- v2.83 LTS
    V2_83 = (2, 83, 0)       # 2.83   - June 3, 2020
    V2_83_0 = (2, 83, 0)
    V2_83_1 = (2, 83, 1)     # 2.83.1 - June 25, 2020
    V2_83_2 = (2, 83, 2)     # 2.83.2 - July 9, 2020
    V2_83_3 = (2, 83, 3)     # 2.83.3 - July 22, 2020
    V2_83_4 = (2, 83, 4)     # 2.83.4 - August 5, 2020
    V2_83_5 = (2, 83, 5)     # 2.83.5 - August 19, 2020
    V2_83_6 = (2, 83, 6)     # 2.83.6 - September 9, 2020
    V2_83_7 = (2, 83, 7)     # 2.83.7 - September 30, 2020
    V2_83_8 = (2, 83, 8)     # 2.83.8 - October 21, 2020
    V2_83_9 = (2, 83, 9)     # 2.83.9 - November 11, 2020
    #
    # --- v2.90
    # API changes since v2.83 -> https://docs.blender.org/api/2.90/change_log.html
    V2_90 = (2, 90, 0)       # 2.90.0 - August 31, 2020
    V2_90_0 = (2, 90, 0)
    V2_90_1 = (2, 90, 1)     # 2.90.1 - September 23, 2020
    #
    # --- v2.91
    V2_91 = (2, 91, 0)       # 2.91.0 - November 25, 2020
    V2_91_0 = (2, 91, 0)

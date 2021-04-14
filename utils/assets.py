
from os import path


ASSET_FOLDER = path.join(path.dirname(path.abspath(__file__)), "../assets")


# ==================================================================================================
def get_asset(name: str) -> str:
    """Given a file asset name returns the full path to such asset.
    WARNING: no checks on file existence are done!

    Arguments:
        name {str} -- asset's file name

    Returns:
        str -- full asset path
    """
    return path.join(ASSET_FOLDER, name)

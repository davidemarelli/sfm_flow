
import logging
import sys
from os import environ

# ==================================================================================================
# Log levels
DISABLED = 0
INFO = logging.INFO
WARNING = logging.WARNING
ERROR = logging.ERROR
CRITICAL = logging.CRITICAL
DEBUG = logging.DEBUG


# ==================================================================================================
def setup_logger(log_level: int = logging.ERROR) -> None:
    """Global logging setup.

    Arguments:
        log_level {int} -- Logging level can be one of:
                            - DISABLED
                            - INFO
                            - WARNING
                            - ERROR
                            - CRITICAL
                            - DEBUG
    """
    disabled = not log_level
    if disabled:
        logging.disable(logging.CRITICAL)
    else:
        logging.disable(logging.NOTSET)
    #
    # log level override for debug
    if 'ADDONS_TO_LOAD' in environ:
        # the VSCode blender development plugin sets this env variable when running in debug.
        # here i use it to toggle logging level for debugging, otherwise on add-on reinstall
        # are restored the default preferences
        log_init_msg = "Logger started with level override `DEBUG` for development!"
        log_level = DEBUG
        # set other libraries logging to fatal only
        flask_logger = logging.getLogger('werkzeug')   # pylint: disable=invalid-name
        flask_logger.setLevel(logging.FATAL)
        urllib_logger = logging.getLogger('urllib3.connectionpool')
        urllib_logger.setLevel(logging.FATAL)
    else:
        log_init_msg = f"Logger started with level {logging.getLevelName(log_level)}"
    #
    # logging setup
    root = logging.getLogger()
    root.setLevel(log_level)
    already_init = next((hdl for hdl in root.handlers if hdl.stream.name == "<stdout>"), None)
    if not already_init:
        handler = logging.StreamHandler(sys.stdout)  # log to stdout
        handler.setLevel(log_level)
        formatter = logging.Formatter("%(asctime)s - %(name)-30s - %(levelname)7s : %(message)s")
        handler.setFormatter(formatter)
        root.addHandler(handler)
        root.info("Logger setup completed! %s", log_init_msg)
    else:
        already_init.setLevel(log_level)
        root.info("Logger already initialized! %s", log_init_msg)

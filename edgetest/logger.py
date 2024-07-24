"""Logging Module.

Module which setsup the basic logging infrustrcuture for the application.
"""

import logging
import sys

# logger formating
BRIEF_FORMAT = "%(levelname)s %(asctime)s - %(name)s: %(message)s"
VERBOSE_FORMAT = (
    "%(levelname)s|%(asctime)s|%(name)s|%(filename)s|"
    "%(funcName)s|%(lineno)d: %(message)s"
)
FORMAT_TO_USE = VERBOSE_FORMAT

# logger levels
DEBUG = logging.DEBUG
INFO = logging.INFO
WARN = logging.WARNING
ERROR = logging.ERROR
CRITICAL = logging.CRITICAL


def get_logger(name=None, log_level=logging.INFO):
    """Set the basic logging features for the application.

    Parameters
    ----------
    name : str, optional
        The name of the logger. Defaults to ``None``
    log_level : int, optional
        The logging level. Defaults to ``logging.INFO``

    Returns
    -------
    logging.Logger
        Returns a Logger obejct which is set with the passed in paramters.
    """
    logging.basicConfig(format=FORMAT_TO_USE, stream=sys.stdout, level=log_level)
    logger = logging.getLogger(name)
    return logger

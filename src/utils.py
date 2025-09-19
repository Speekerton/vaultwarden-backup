import logging
import os
import sys

import psutil


def is_systemd_child():
    try:
        parent = psutil.Process(os.getppid())
        return parent.name() == "systemd"
    except Exception:
        return False


def setup_logging(verbosity_level: int):
    levels = [logging.INFO, logging.DEBUG]
    level = levels[min(verbosity_level, len(levels) - 1)]

    if is_systemd_child():
        log_format = "%(name)s - %(levelname)s - %(message)s"
    else:
        log_format = "%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s"

    logging.basicConfig(
        level=level,
        format=log_format,
        datefmt="%Y-%m-%d %H:%M:%S",
        stream=sys.stdout,
        force=True,
    )

import logging
import sys
import os
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
        log_format = "%(module)s - %(levelname)s - %(message)s"
    else:
        log_format = "%(asctime)s - %(module)s - %(levelname)s - %(message)s"

    logging.basicConfig(
        level=level,
        format=log_format,
        datefmt="%Y-%m-%d %H:%M:%S",
        stream=sys.stdout,
    )

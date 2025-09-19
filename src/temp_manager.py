import logging
import tempfile
from contextlib import contextmanager

l = logging.getLogger(__name__)  # noqa: E741


@contextmanager
def secure_temp_directory():
    """Create a secure temporary directory that auto-cleans."""
    with tempfile.TemporaryDirectory(prefix="vaultwarden-backup-") as temp_dir:
        l.debug(f"Created temporary directory: {temp_dir}")
        yield temp_dir
        l.debug(f"Cleaning up temporary directory: {temp_dir}")

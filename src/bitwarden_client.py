from plumbum import local
from plumbum.cmd import bw
from contextlib import nullcontext
import logging
import os
import tempfile

l = logging.getLogger(__name__)  # noqa: E741

SCRIPT_ETC_DIR = "/etc/vaultwarden-backup"


class Bw:
    def __init__(self, cfg):
        self.cfg = cfg

    def __enter__(self):
        self._configure()
        self._login()
        self._sync()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._logout()
        return False

    def _appdata_env(self):
        return (
            local.env(BITWARDENCLI_APPDATA_DIR=SCRIPT_ETC_DIR)
            if os.path.isdir(SCRIPT_ETC_DIR)
            else nullcontext()
        )

    def _configure(self):
        l.info("Configure vaultwarden server...")
        with self._appdata_env():
            bw["config", "server", self.cfg.vaultwarden_url]()
        l.info("Vaultwarden server configured")

    def _login(self):
        l.info("Login into vaultwarden...")
        try:
            with self._appdata_env():
                with local.env(
                    BW_CLIENTID=self.cfg.client_id,
                    BW_CLIENTSECRET=self.cfg.client_secret,
                ):
                    bw["login", "--apikey"]()
            l.info("Logged in")
        except Exception as e:
            if "You are already logged in" in str(e):
                l.warning("Already logged in")
                self._logout()
                self._login()
            else:
                raise

    def _logout(self):
        l.info("Logout from vaultwarden...")
        try:
            with self._appdata_env():
                bw["logout"]()
            l.info("Logged out")
        except Exception as e:
            l.warning(f"Logout failed (may already be logged out): {e}")

    def _sync(self):
        l.info("Sync vaultwarden...")
        try:
            with self._appdata_env():
                bw["sync"]()
            l.info("Vaultwarden synced")
        except Exception as e:
            l.error(f"Sync failed: {e}")
            raise

    def export(self):
        """Export vaultwarden data using secure password handling."""
        l.info("Export vaultwarden data to json format...")
        password_file = None
        try:
            # Create temporary file for password (no chmod to avoid container issues)
            fd, password_file = tempfile.mkstemp(prefix="bw_export_pwd_", suffix=".tmp")
            with os.fdopen(fd, "w") as f:
                f.write(self.cfg.master_password)

            with self._appdata_env():
                # Use --passwordfile instead of piping echo
                bw_export = bw[
                    "export",
                    "--output",
                    self.cfg.vaultwarden_json_path(),
                    "--format",
                    "json",
                    "--passwordfile",
                    password_file,
                ]
                bw_export()

            l.info("Vaultwarden data exported to json format")

        except Exception as e:
            l.error(f"Export failed: {e}")
            raise
        finally:
            # Clean up password file
            if password_file and os.path.exists(password_file):
                os.unlink(password_file)
                l.debug("Temporary password file cleaned up")

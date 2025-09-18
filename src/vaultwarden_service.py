from plumbum.cmd import cp, systemctl
import logging

l = logging.getLogger(__name__)  # noqa: E741


class VaultwardenService:
    def __init__(self, cfg):
        self.cfg = cfg

    def __enter__(self):
        self._stop()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._start()
        return False

    def _start(self):
        l.info("Start vaultwarden systemd service...")
        systemctl["start", "vaultwarden.service"]()
        l.info("Vaultwarden systemd service started")

    def _stop(self):
        l.info("Stop vaultwarden systemd service...")
        systemctl["stop", "vaultwarden.service"]()
        l.info("Vaultwarden systemd service stopped")

    def backup(self):
        l.info("Backup vaultwarden data...")
        cp["-a", f"{self.cfg.data_dir}", self.cfg.vaultwarden_data_backup_path()]()
        l.info("Vaultwarden data backuped to temporary directory")

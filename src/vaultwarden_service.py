import logging
import os
import shutil
import sqlite3

l = logging.getLogger(__name__)  # noqa: E741


class VaultwardenService:
    def __init__(self, cfg):
        self.cfg = cfg

    def __enter__(self):
        # Don't stop the service - SQLite supports online backup
        l.info("Using online backup (service will remain running)")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # Don't need to restart since we never stopped
        l.info("Archive backup completed, service was never interrupted")
        return False

    def backup(self):
        """Backup vaultwarden data files for archive creation."""
        l.info("Backup vaultwarden data (online backup)...")

        # Create backup directory first
        os.makedirs(self.cfg.vaultwarden_data_backup_path(), exist_ok=True)

        # SQLite online backup with timeout (equivalent to CLI .backup command)
        db_source = f"{self.cfg.data_dir}/db.sqlite3"
        db_backup = f"{self.cfg.vaultwarden_data_backup_path()}/db.sqlite3"

        if os.path.exists(db_source):
            l.info(f"Backing up database: {db_source} -> {db_backup}")
            try:
                # Use 30-second timeout like the reference script
                source_conn = sqlite3.connect(
                    f"file:{db_source}?mode=ro", uri=True, timeout=30.0
                )
                backup_conn = sqlite3.connect(db_backup)
                source_conn.backup(backup_conn)
                source_conn.close()
                backup_conn.close()
                l.info("Database backup completed using Online Backup API")
            except Exception as e:
                l.error(f"Database backup failed: {e}")
                raise
        else:
            l.warning(f"Database file not found: {db_source}")

        # Backup files as specified in official Vaultwarden wiki
        files_to_backup = [
            "config.json",  # Admin config (recommended)
            "rsa_key.der",  # Authentication tokens (recommended)
            "rsa_key.pem",
            "rsa_key.pub.der",
            "rsa_key.pub.pem",
        ]

        directories_to_backup = [
            "attachments",  # File attachments (required)
            "sends",  # Send attachments (optional but included)
        ]

        # Copy individual files
        for filename in files_to_backup:
            source_file = f"{self.cfg.data_dir}/{filename}"
            if os.path.exists(source_file):
                l.info(f"Backing up file: {filename}")
                shutil.copy2(
                    source_file, f"{self.cfg.vaultwarden_data_backup_path()}/{filename}"
                )

        # Copy directories
        for dirname in directories_to_backup:
            source_dir = f"{self.cfg.data_dir}/{dirname}"
            if os.path.exists(source_dir):
                l.info(f"Backing up directory: {dirname}")
                shutil.copytree(
                    source_dir,
                    f"{self.cfg.vaultwarden_data_backup_path()}/{dirname}",
                    dirs_exist_ok=True,
                )

        # Skip icon_cache as it's optional and not worth backing up according to wiki

        l.info("Vaultwarden data backup completed (service kept running)")

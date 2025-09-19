import hashlib
import logging
import os
import shutil
from datetime import datetime

from plumbum.cmd import gpg, mkdir, mv, rclone, tar

l = logging.getLogger(__name__)  # noqa: E741


def generate_checksums(file_path):
    """Generate MD5 and SHA1 checksums for a file."""
    md5_hash = hashlib.md5()
    sha1_hash = hashlib.sha1()

    try:
        with open(file_path, "rb") as f:
            # Read file in chunks to handle large files efficiently
            for chunk in iter(lambda: f.read(4096), b""):
                md5_hash.update(chunk)
                sha1_hash.update(chunk)

        md5_sum = md5_hash.hexdigest()
        sha1_sum = sha1_hash.hexdigest()

        l.info(f"MD5: {md5_sum}  {os.path.basename(file_path)}")
        l.info(f"SHA1: {sha1_sum}  {os.path.basename(file_path)}")

        return md5_sum, sha1_sum

    except Exception as e:
        l.error(f"Failed to generate checksums for {file_path}: {e}")
        raise


def create_backup(cfg):
    backup_name = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    backup_dir = f"{cfg.backups_dir}/{backup_name}"

    try:
        l.info(f"Create backup {backup_dir}...")
        mkdir["-p", backup_dir]()
        mv[cfg.encrypted_archive_path(), backup_dir]()
        mv[cfg.keepass_db_path(), backup_dir]()
        l.info("Backup created successfully")
    except Exception as e:
        l.error(f"Failed to create backup: {e}")
        raise


def rotate_backups(cfg):
    if not os.path.exists(cfg.backups_dir):
        l.info("Backups directory doesn't exist, skipping rotation")
        return

    try:
        backups = [
            os.path.join(cfg.backups_dir, f) for f in os.listdir(cfg.backups_dir)
        ]
        backups = [f for f in backups if os.path.isdir(f)]
        backups.sort(key=lambda f: os.path.getmtime(f), reverse=True)

        to_delete = backups[cfg.backups_keep_last :]

        l.info("Delete old backups...")
        for d in to_delete:
            try:
                shutil.rmtree(d)
                l.info(f"Backup deleted: {d}")
            except Exception as e:
                l.error(f"Error deleting backup {d}: {e}")
        l.info("Backups deleted")
    except Exception as e:
        l.error(f"Failed to rotate backups: {e}")
        raise


def sync_backups(cfg):
    if not cfg.remotes:
        l.info("No remotes configured, skipping sync")
        return

    try:
        l.info("Sync backups...")
        for remote in cfg.remotes:
            l.info(f"Syncing {remote}...")
            for attempt in range(0, cfg.sync_attempts):
                try:
                    l.debug(f"Attempt {attempt}")
                    rclone["sync", cfg.backups_dir, remote, "--progress"]()
                    l.info(f"{remote} synced")
                    break
                except Exception as e:
                    l.error(f"Failed to sync {remote}: {e}")
                    if attempt == cfg.sync_attempts - 1:
                        l.warning("This was the last attempt")

        l.info("Backups synced")
    except Exception as e:
        l.error(f"Failed to sync backups: {e}")
        raise


def do_archive_backup(cfg):
    from vaultwarden_service import VaultwardenService

    try:
        with VaultwardenService(cfg) as vw:
            vw.backup()
        mkdir["-p", cfg.archive_dir_path()]()
        mv[cfg.vaultwarden_data_backup_path(), f"{cfg.archive_dir_path()}/"]()
        mv[cfg.vaultwarden_json_path(), f"{cfg.archive_dir_path()}/"]()

        l.info("Compress vaultwarden data into tar archive...")
        tar["-czf", cfg.archive_path(), "-C", cfg.temp_dir, cfg.archive_dir_name()]()
        l.info("Vaultwarden data archived")

        # Generate checksums for the unencrypted archive
        l.info("Generating checksums for archive...")
        generate_checksums(cfg.archive_path())

        l.info("Encrypt archive with GPG...")
        gpg_process = gpg[
            "--batch",
            "--yes",
            "--passphrase-fd",
            "0",
            "--symmetric",
            "--cipher-algo",
            "AES256",
            cfg.archive_path(),
        ]
        gpg_process(stdin=cfg.master_password.encode())
        l.info("Archive encrypted")

        # Generate checksums for the encrypted archive
        l.info("Generating checksums for encrypted archive...")
        generate_checksums(cfg.encrypted_archive_path())

    except Exception as e:
        l.error(f"Failed to create archive backup: {e}")
        raise


def do_keepass_backup(cfg):
    import json

    import keepass
    from bitwarden_client import Bw

    try:
        with Bw(cfg) as bw:
            bw.export()

        with open(cfg.vaultwarden_json_path(), "r") as vaultwarden_json_file:
            keepass.run(
                cfg.keepass_db_path(),
                cfg.master_password,
                json.load(vaultwarden_json_file),
            )

        l.info("KeePassXC database created successfully")

    except Exception as e:
        l.error(f"Failed to create KeePassXC backup: {e}")
        raise

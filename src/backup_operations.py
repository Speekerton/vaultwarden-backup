from datetime import datetime
from plumbum.cmd import tar, gpg, mv, mkdir, rclone
import logging
import os
import shutil

l = logging.getLogger(__name__)  # noqa: E741


def create_backup(cfg):
    backup_name = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    backup_dir = f"{cfg.backups_dir}/{backup_name}"

    l.info(f"Create backup {backup_dir}...")

    mkdir["-p", backup_dir]()
    mv[cfg.encrypted_archive_path(), backup_dir]()
    mv[cfg.keepass_db_path(), backup_dir]()

    l.info("Backup created")


def rotate_backups(cfg):
    if not os.path.exists(cfg.backups_dir):
        l.info("Backups directory doesn't exist, skipping rotation")
        return

    backups = [os.path.join(cfg.backups_dir, f) for f in os.listdir(cfg.backups_dir)]
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


def sync_backups(cfg):
    if not cfg.remotes:
        l.info("No remotes configured, skipping sync")
        return

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
                    l.warn("This was the last attempt")

    l.info("Backups synced")


def do_archive_backup(cfg):
    from vaultwarden_service import VaultwardenService

    with VaultwardenService(cfg) as vw:
        vw.backup()
    mkdir["-p", cfg.archive_dir_path()]()
    mv[cfg.vaultwarden_data_backup_path(), f"{cfg.archive_dir_path()}/"]()
    mv[cfg.vaultwarden_json_path(), f"{cfg.archive_dir_path()}/"]()

    l.info("Compress vaultwarden data into tar archive...")
    tar["-cJf", cfg.archive_path(), "-C", cfg.temp_dir, cfg.archive_dir_name()]()
    l.info("Vaultwarden data archived")

    l.info("Encrypt archive with GPG...")
    gpg[
        "--batch",
        "--yes",
        "--passphrase",
        cfg.master_password,
        "--symmetric",
        "--cipher-algo",
        "AES256",
        cfg.archive_path(),
    ]()
    l.info("Archive encrypted")


def do_keepass_backup(cfg):
    from bitwarden_client import Bw
    import keepass
    import json

    with Bw(cfg) as bw:
        bw.export()

    with open(cfg.vaultwarden_json_path(), "r") as vaultwarden_json_file:
        keepass.run(
            cfg.keepass_db_path(), cfg.master_password, json.load(vaultwarden_json_file)
        )

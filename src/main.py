#!/usr/bin/env python

from datetime import datetime
from dotenv import load_dotenv
from plumbum import local
from plumbum.cmd import cp, tar, gpg, mv, systemctl, mktemp, bw, mkdir, rclone, echo
from datetime import datetime
from contextlib import nullcontext
import logging
import os
import sys
import argparse
import keepass
import json
import utils
import time
import signal
import shutil

l = logging.getLogger(__name__)
SCRIPT_PATH = os.path.abspath(__file__)
SCRIPT_DIR = os.path.dirname(SCRIPT_PATH)
SCRIPT_ETC_DIR = "/etc/vaultwarden-backup"

class VaultwardenService:
    def __init__(self, cfg):
        self.cfg = cfg
        
    def __enter__(self):
        self._stop()
        # Initialize or allocate the resource here
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._start()
        # Cleanup or release the resource here
        # Return False to propagate exceptions, True to suppress
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


class Bw:
    def __init__(self, cfg):
        self.cfg = cfg
    
    def __enter__(self):
        self._configure()
        self._login()
        self._sync()
        # Initialize or allocate the resource here
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._logout()
        # Cleanup or release the resource here
        # Return False to propagate exceptions, True to suppress
        return False

    def _appdata_env(self):
        return local.env(BITWARDENCLI_APPDATA_DIR=SCRIPT_ETC_DIR) if os.path.isdir(SCRIPT_ETC_DIR) else nullcontext()

    def _configure(self):
        l.info("Configure vaultwarden server...")
        with self._appdata_env():
            bw["config", "server", self.cfg.vaultwarden_url]()
        l.info("Vaultwarden server configured")
        
    def _login(self):
        l.info("Login into vaultwarden...")
        try:
            with self._appdata_env():
                with local.env(BW_CLIENTID=self.cfg.client_id, BW_CLIENTSECRET=self.cfg.client_secret):
                    bw["login", "--apikey"]()
            l.info("Logged in")
        except Exception as e:
            if "You are already logged in" in str(e):
                l.warning("Alredy logged in")
                self._logout()
                self._login()
            else:
                raise
        
    def _logout(self):
        l.info("Logout from vaultwarden...")
        with self._appdata_env():
            bw["logout"]()
        l.info("Logged out")
        
    def _sync(self):
        l.info("Sync vaultwarden...")
        with self._appdata_env():
            bw["sync"]()
        l.info("Vaultwarden synced")
        
    def export(self):
        l.info("Export vaultwarden data to json format...")
        with self._appdata_env():
            (echo["-e", self.cfg.master_password] | bw["export", "--output", self.cfg.vaultwarden_json_path(), "--format", "json"])()
        l.info("Vaultwarden data exported to json format")


def create_keepass_db(cfg):
    with open(cfg.vaultwarden_json_path(), 'r') as vaultwarden_json_file:
        keepass.run(cfg.keepass_db_path(), cfg.master_password, json.load(vaultwarden_json_file))


def do_keepass_backup(cfg):
    with Bw(cfg) as bw:
        bw.export()
    create_keepass_db(cfg)
    

def do_archive_backup(cfg):
    with VaultwardenService(cfg) as vw:
        vw.backup()
    mkdir["-p", cfg.archive_dir_path()]()
    mv[cfg.vaultwarden_data_backup_path(), f"{cfg.archive_dir_path()}/"]()
    mv[cfg.vaultwarden_json_path(), f"{cfg.archive_dir_path()}/"]()
    
    l.info("Compress vaultwarden data into tar archive...")
    tar["-cJf", cfg.archive_path(), "-C", cfg.temp_dir, cfg.archive_dir_name()]()
    l.info("Vaultwarden data archived")
    
    l.info("Encrypt archive with GPG...")
    gpg["--batch", "--yes", "--passphrase", cfg.master_password, "--symmetric", "--cipher-algo", "AES256", cfg.archive_path()]()
    l.info("Archive encrypted")


def create_backup(cfg):
    backup_name = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    backup_dir = f"{cfg.backups_dir}/{backup_name}"
    
    l.info(f"Create backup {backup_dir}...")
    
    mkdir["-p", backup_dir]()
    mv[cfg.encrypted_archive_path(), backup_dir]()
    mv[cfg.keepass_db_path(), backup_dir]()
    
    l.info("Backup created")


def rotate_backups(cfg):
    backups = [os.path.join(cfg.backups_dir, f) for f in os.listdir(cfg.backups_dir)]
    backups.sort(key=lambda f: os.path.getmtime(f), reverse=True)
    
    to_delete = backups[cfg.backups_keep_last:]
    
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


# === Cleanup on Exit ===
def cleanup(cfg):
    shutil.rmtree(cfg.temp_dir)
    l.debug(f"Temporary dir {cfg.temp_dir} deleted")


# === Error Handling ===
def on_error(exception):
    """Handle errors."""
    l.error(f"An error occurred: {exception}")


# Define the Config structure to store the parsed arguments
class Config:
    def __init__(self, master_password=None, client_id=None, client_secret=None, data_dir=None, temp_dir=None, backups_dir=None, backups_keep_last=None, remotes=None, vaultwarden_url=None, sync_attempts=None):
        self.master_password = master_password
        self.client_id = client_id
        self.client_secret = client_secret
        self.data_dir = data_dir
        self.temp_dir = temp_dir
        self.backups_dir = backups_dir
        self.backups_keep_last = backups_keep_last
        self.remotes = remotes
        self.vaultwarden_url = vaultwarden_url
        self.sync_attempts = sync_attempts

    def __str__(self):
        return (f"Config(master_password={self.master_password}, "
                f"client_id={self.client_id}, "
                f"client_secret={self.client_secret}, "
                f"data_dir={self.data_dir}, "
                f"temp_dir={self.temp_dir}, "
                f"backups_dir={self.backups_dir}, "
                f"backups_keep_last={self.backups_keep_last}, "
                f"remotes={self.remotes}, "
                f"vaultwarden_url={self.vaultwarden_url}, "
                f"sync_attempts={self.sync_attempts})")

    def verify(self):
        if not self.master_password:
            raise Exception("'--master-password' or 'MASTER_PASSWORD' is required")
        if not self.client_id:
            raise Exception("'--client-id' or 'CLIENT_ID' is required")
        if not self.client_secret:
            raise Exception("'--client-secret' or 'CLIENT_SECRET' is required")
        if not self.data_dir:
            raise Exception("'--data-dir' or 'DATA_DIR' is required")
        if not self.temp_dir:
            raise Exception("Temporary directory is empty???")
        if not self.backups_dir:
            raise Exception("'--backups-dir' or 'BACKUPS_DIR' is required")
        if not self.backups_keep_last:
            raise Exception("'--backups-keep-last' or 'BACKUPS_KEEP_LAST' is required")
        if self.backups_keep_last <= 0:
            raise Exception("'--backups-keep-last' or 'BACKUPS_KEEP_LAST' should be positive number")
        # if not self.remotes:
            # raise Exception("'--remotes' or 'REMOTES' is required")
        
        if not self.remotes:
            self.remotes = []
        
        if not self.vaultwarden_url:
            raise Exception("'--vaultwarden-url' or 'VAULTWARDEN_URL' is required")
        if not self.sync_attempts:
            raise Exception("'--sync-attempts' or 'SYNC_ATTEMPTS' is required")
        if self.sync_attempts <= 0:
            raise Exception("'--sync-attempts' or 'SYNC_ATTEMPTS' should be positive number")
            

    def keepass_db_path(self):
        return f"{self.temp_dir}/passwords.kdbx"
        
    def vaultwarden_json_path(self):
        return f"{self.temp_dir}/vaultwarden.json"
        
    def vaultwarden_data_backup_path(self):
        return f"{self.temp_dir}/data"
        
    def archive_dir_name(self):
        return f"arch"
        
    def archive_dir_path(self):
        return f"{self.temp_dir}/{self.archive_dir_name()}"
        
    def archive_path(self):
        return f"{self.archive_dir_path()}.tar.gz"
        
    def encrypted_archive_path(self):
        return f"{self.archive_dir_path()}.tar.gz.gpg"

def parse_arguments():
    load_dotenv()
    
    # Set up argparse for command-line argument parsing
    parser = argparse.ArgumentParser(description="Script for interacting with Vaultwarden and KeePass.")
    
    parser.add_argument("-v", "--verbose", action="count", help="Logging verbosity level.")
    parser.add_argument("--master-password", type=str, help="Vaultwarden master password.")
    parser.add_argument("--client-id", type=str, help="Vaultwarden client ID.")
    parser.add_argument("--client-secret", type=str, help="Vaultwarden client secret.")
    parser.add_argument("--data-dir", type=str, help="Path to the vaultwarden data directory.")
    parser.add_argument("--backups-dir", type=str, help="Backups directory.")
    parser.add_argument("--backups-keep-last", type=int, help="Last N backups that need to keep.")
    parser.add_argument("--remotes", nargs="+", type=str, help="List of rclone remote paths.")
    parser.add_argument("--vaultwarden-url", type=str, help="Vaultwarden server URL.")
    parser.add_argument("--sync-attempts", type=int, help="Number of attempts to synchronize with remotes")

    # Parse command-line arguments
    args = parser.parse_args()

    # Retrieve parameters from command-line arguments or environment variables
    verbose = int(args.verbose or os.getenv("VERBOSE") or 0)
    utils.setup_logging(verbose)
    
    master_password = args.master_password or os.getenv("MASTER_PASSWORD")
    client_id = args.client_id or os.getenv("CLIENT_ID")
    client_secret = args.client_secret or os.getenv("CLIENT_SECRET")
    data_dir = args.data_dir or os.getenv("DATA_DIR")
    backups_keep_last = int(args.backups_keep_last or os.getenv("BACKUPS_KEEP_LAST") or 7)
    remotes = args.remotes or os.getenv("REMOTES") and os.getenv("REMOTES").split() or None
    vaultwarden_url = args.vaultwarden_url or os.getenv("VAULTWARDEN_URL")
    sync_attempts = int(args.sync_attempts or os.getenv("SYNC_ATTEMPTS") or 3)
    
    temp_dir = mktemp["-d", "-t", "vaultwarden-backup.XXXXXXXXXXXXXXXXXXX"]().rstrip()
    backups_dir = args.backups_dir or os.getenv('BACKUPS_DIR') or f"{SCRIPT_DIR}/backups"

    # Return a Config object
    return Config(master_password, client_id, client_secret, data_dir, temp_dir, backups_dir, backups_keep_last, remotes, vaultwarden_url, sync_attempts)


# Factory function to create a signal handler with access to config
def make_signal_handler(cfg):
    def handler(sig, frame):
        l.info(f"Received signal {sig}. Exiting gracefully...")
        cleanup(cfg)
        sys.exit(0)
    return handler


def main():
    cfg = parse_arguments()

    # Attach signal handler
    signal_handler = make_signal_handler(cfg)
    signal.signal(signal.SIGINT, signal_handler)   # Ctrl+C
    signal.signal(signal.SIGTERM, signal_handler)  # Termination signal from system
    
    try:
        cfg.verify()
        do_keepass_backup(cfg)
        do_archive_backup(cfg)
        create_backup(cfg)
        rotate_backups(cfg)
        sync_backups(cfg)
        cleanup(cfg)
        sys.exit(0)
    except Exception as e:
        on_error(e)
        cleanup(cfg)
        sys.exit(1)


if __name__ == "__main__":
    main()
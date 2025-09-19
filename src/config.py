import logging
import os

from dotenv import load_dotenv

l = logging.getLogger(__name__)  # noqa: E741


class Config:
    def __init__(
        self,
        master_password=None,
        client_id=None,
        client_secret=None,
        data_dir=None,
        temp_dir=None,
        backups_dir=None,
        backups_keep_last=None,
        remotes=None,
        vaultwarden_url=None,
        sync_attempts=None,
    ):
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
        return (
            f"Config(master_password=***REDACTED***, "
            f"client_id={self.client_id}, "
            f"client_secret=***REDACTED***, "
            f"data_dir={self.data_dir}, "
            f"temp_dir={self.temp_dir}, "
            f"backups_dir={self.backups_dir}, "
            f"backups_keep_last={self.backups_keep_last}, "
            f"remotes={self.remotes}, "
            f"vaultwarden_url={self.vaultwarden_url}, "
            f"sync_attempts={self.sync_attempts})"
        )

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
            raise Exception("Temporary directory is empty")
        if not self.backups_dir:
            raise Exception("'--backups-dir' or 'BACKUPS_DIR' is required")
        if not self.backups_keep_last:
            raise Exception("'--backups-keep-last' or 'BACKUPS_KEEP_LAST' is required")
        if self.backups_keep_last <= 0:
            raise Exception(
                "'--backups-keep-last' or 'BACKUPS_KEEP_LAST' should be positive number"
            )

        # Handle empty remotes gracefully
        if not self.remotes:
            self.remotes = []

        if not self.vaultwarden_url:
            raise Exception("'--vaultwarden-url' or 'VAULTWARDEN_URL' is required")
        if not self.sync_attempts:
            raise Exception("'--sync-attempts' or 'SYNC_ATTEMPTS' is required")
        if self.sync_attempts <= 0:
            raise Exception(
                "'--sync-attempts' or 'SYNC_ATTEMPTS' should be positive number"
            )

    def keepass_db_path(self):
        return f"{self.temp_dir}/passwords.kdbx"

    def vaultwarden_json_path(self):
        return f"{self.temp_dir}/vaultwarden.json"

    def vaultwarden_data_backup_path(self):
        return f"{self.temp_dir}/data"

    def archive_dir_name(self):
        return "arch"

    def archive_dir_path(self):
        return f"{self.temp_dir}/{self.archive_dir_name()}"

    def archive_path(self):
        return f"{self.archive_dir_path()}.tar.gz"

    def encrypted_archive_path(self):
        return f"{self.archive_dir_path()}.tar.gz.gpg"


def parse_config_from_args(args):
    """Parse configuration from command line arguments and environment variables."""
    load_dotenv()

    master_password = args.master_password or os.getenv("MASTER_PASSWORD")
    client_id = args.client_id or os.getenv("CLIENT_ID")
    client_secret = args.client_secret or os.getenv("CLIENT_SECRET")
    data_dir = args.data_dir or os.getenv("DATA_DIR")
    backups_keep_last = int(
        args.backups_keep_last or os.getenv("BACKUPS_KEEP_LAST") or 7
    )

    # FIXED: Robust REMOTES parsing
    if args.remotes:
        remotes = args.remotes
    else:
        remotes_env = os.getenv("REMOTES")
        if remotes_env is not None and remotes_env.strip():
            # Split by whitespace and filter out empty strings
            remotes = [r.strip() for r in remotes_env.split() if r.strip()]
        else:
            remotes = []

    vaultwarden_url = args.vaultwarden_url or os.getenv("VAULTWARDEN_URL")
    sync_attempts = int(args.sync_attempts or os.getenv("SYNC_ATTEMPTS") or 3)

    script_dir = os.path.dirname(os.path.abspath(__file__))
    backups_dir = (
        args.backups_dir or os.getenv("BACKUPS_DIR") or f"{script_dir}/backups"
    )

    return Config(
        master_password=master_password,
        client_id=client_id,
        client_secret=client_secret,
        data_dir=data_dir,
        temp_dir=None,  # Will be set later
        backups_dir=backups_dir,
        backups_keep_last=backups_keep_last,
        remotes=remotes,
        vaultwarden_url=vaultwarden_url,
        sync_attempts=sync_attempts,
    )

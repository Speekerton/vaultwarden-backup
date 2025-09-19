import argparse
import logging
import sys

from backup_operations import (
    create_backup,
    do_archive_backup,
    do_keepass_backup,
    rotate_backups,
    sync_backups,
)
from config import parse_config_from_args
from temp_manager import secure_temp_directory
from utils import setup_logging

l = logging.getLogger(__name__)  # noqa: E741


def on_error(exception):
    """Handle errors."""
    l.error(f"An error occurred: {exception}")


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Script for interacting with Vaultwarden and KeePass."
    )

    parser.add_argument(
        "-v", "--verbose", action="count", help="Logging verbosity level."
    )
    parser.add_argument(
        "--master-password", type=str, help="Vaultwarden master password."
    )
    parser.add_argument("--client-id", type=str, help="Vaultwarden client ID.")
    parser.add_argument("--client-secret", type=str, help="Vaultwarden client secret.")
    parser.add_argument(
        "--data-dir", type=str, help="Path to the vaultwarden data directory."
    )
    parser.add_argument("--backups-dir", type=str, help="Backups directory.")
    parser.add_argument(
        "--backups-keep-last", type=int, help="Last N backups that need to keep."
    )
    parser.add_argument(
        "--remotes", nargs="+", type=str, help="List of rclone remote paths."
    )
    parser.add_argument("--vaultwarden-url", type=str, help="Vaultwarden server URL.")
    parser.add_argument(
        "--sync-attempts",
        type=int,
        help="Number of attempts to synchronize with remotes",
    )

    return parser.parse_args()


def main():
    args = parse_arguments()

    # Setup logging
    verbose = int(args.verbose or 0)
    setup_logging(verbose)

    # Parse config without temp_dir first
    config_partial = parse_config_from_args(args)

    # Use secure temporary directory
    with secure_temp_directory() as temp_dir:
        # Create final config with temp_dir
        config_partial.temp_dir = temp_dir
        cfg = config_partial

        try:
            cfg.verify()
            do_keepass_backup(cfg)
            do_archive_backup(cfg)
            create_backup(cfg)
            rotate_backups(cfg)
            sync_backups(cfg)
            l.info("Backup completed successfully")
        except Exception as e:
            on_error(e)
            sys.exit(1)


if __name__ == "__main__":
    main()

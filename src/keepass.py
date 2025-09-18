#!/usr/bin/env python

import argparse
import json
import pykeepass
import logging
import utils
from uuid import uuid4

l = logging.getLogger(__name__)  # noqa: E741


# Create a new KeePassXC database
def create_keepass_db(db_path, master_password):
    l.info("Create keepass database...")
    kp = pykeepass.create_database(db_path, master_password)
    l.info("Keepass database created")
    return kp


# Add groups
def make_groups(kp, folders_raw):
    l.info("Add groups to keepass db...")
    groups = {}
    for folder in folders_raw:
        folder_id = folder["id"]
        folder_name = folder["name"]
        group = kp.add_group(kp.root_group, folder_name)  # Add the group to KeePass
        groups[folder_id] = group
        l.debug(f"Group added: {folder_name}")
    l.info("Groups added")
    return groups


# Add entries in KeePass
def add_entries(kp, items_raw, groups):
    l.info("Add entries to keepass db...")
    for item in items_raw:
        name = item.get("name", f"Nameless-{str(uuid4())}")
        username = item.get("login", {}).get("username", "")
        password = item.get("login", {}).get("password", "")
        url = item.get("login", {}).get("uris", [])
        url = url[0].get("uri") if url else None
        notes = item.get("notes")
        folder_id = item.get("folderId")
        group = groups.get(folder_id, kp.root_group)

        # Create an entry in KeePass
        kp.add_entry(group, name, username, password, url=url, notes=notes)

        l.debug(f"Entry added: {name}")
    l.info("Entries added")


def run(keepass_db, keepass_password, vaultwarden_json):
    # Step 1: Load data from JSON
    folders_raw = vaultwarden_json["folders"]
    items_raw = vaultwarden_json["items"]

    # Step 2: Create the KeePass db
    kp = create_keepass_db(keepass_db, keepass_password)

    # Step 3: Add groups to KeePass db
    groups = make_groups(kp, folders_raw)

    # Step 4: Add entries
    add_entries(kp, items_raw, groups)

    # Step 5: Save the database after adding all entries
    kp.save(keepass_db)


# Load data from the JSON file
def load_json(json_file):
    with open(json_file, "r") as f:
        return json.load(f)


def main():
    parser = argparse.ArgumentParser(
        description="Convert Vaultwarden export JSON to KeePass database."
    )
    parser.add_argument(
        "-v", "--verbose", action="count", default=0, help="Logging verbosity level"
    )
    parser.add_argument(
        "--keepass-db",
        required=True,
        help="Path to the KeePass database file to create",
    )
    parser.add_argument(
        "--keepass-password",
        required=True,
        help="Master password for the KeePass database",
    )
    parser.add_argument(
        "--vaultwarden-json",
        required=True,
        help="Path to the Vaultwarden JSON export file",
    )

    args = parser.parse_args()

    utils.setup_logging(args.verbose)
    vaultwarden_json = load_json(args.vaultwarden_json)
    run(args.keepass_db, args.keepass_password, vaultwarden_json)


if __name__ == "__main__":
    main()

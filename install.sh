#!/usr/bin/env bash

set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

main() {
    echo "Installing python dependencies..."
    python3 -m venv "${SCRIPT_DIR}/.venv"
    source "${SCRIPT_DIR}/.venv/bin/activate"
    pip install -r "${SCRIPT_DIR}/requirements.txt"
    deactivate
    echo "Success!"

    echo "Copy systemd services"
    cp "${SCRIPT_DIR}/systemd/vaultwarden-backup.service" /etc/systemd/system
    cp "${SCRIPT_DIR}/systemd/vaultwarden-backup.timer" /etc/systemd/system
    sed -i "s|{{project_dir}}|${SCRIPT_DIR}|g" /etc/systemd/system/vaultwarden-backup.service
    systemctl daemon-reexec
    systemctl daemon-reload
    echo "Success!"

    echo "Copy .env"
    mkdir -p "/etc/vaultwarden-backup"
    cp "${SCRIPT_DIR}/example.env" "/etc/vaultwarden-backup/.env"
    echo "Success!"

    echo "Done"
}

main

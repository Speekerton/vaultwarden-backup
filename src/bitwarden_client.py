#!/usr/bin/env python

from plumbum import local
from plumbum.cmd import bw, echo
from contextlib import nullcontext
import logging
import os

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
            (
                echo["-e", self.cfg.master_password]
                | bw[
                    "export",
                    "--output",
                    self.cfg.vaultwarden_json_path(),
                    "--format",
                    "json",
                ]
            )()
        l.info("Vaultwarden data exported to json format")

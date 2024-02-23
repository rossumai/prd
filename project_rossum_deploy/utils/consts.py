from enum import StrEnum
import json
import logging
import os
from pathlib import Path
import re

import click


logging.basicConfig(level=logging.INFO)
logging.getLogger("httpx").setLevel(logging.ERROR)

DEBUG_MODE = os.environ.get("DEBUG", "false").lower() == "true"

API_SUFFIX_RE = re.compile(r"/api/v\d+$")

ATTRIBUTE_OVERRIDE_TARGET_REFERENCE_KEYWORD = "$prd_ref"
ATTRIBUTE_OVERRIDE_SOURCE_REFERENCE_KEYWORD = "$source_value"


class Settings:
    def __init__(self):
        if DEBUG_MODE:
            return

        cred_path = Path("./") / self.CREDENTIALS_FILENAME
        if not cred_path.exists():
            click.echo(
                f"WARNING: {self.CREDENTIALS_FILENAME} not found in the current directory."
            )
            return

        credentials = json.loads(cred_path.read_text())

        self.SOURCE_API_BASE = credentials["source"]["api_base"]
        self.SOURCE_USERNAME = credentials["source"].get("username", None)
        self.SOURCE_PASSWORD = credentials["source"].get("password", None)
        self.SOURCE_TOKEN = credentials["source"].get("token", None)

        if not credentials.get("use_same_org_as_target", False):
            self.IS_PROJECT_IN_SAME_ORG = False
            if "target" not in credentials or not credentials.get("target", {}).get(
                "api_base", ""
            ):
                raise click.ClickException(
                    'Missing target credentials. If you are targetting the same org, set "use_same_org_as_target": true.'
                )
            self.TARGET_API_BASE = credentials["target"]["api_base"]
            self.TARGET_USERNAME = credentials["target"].get("username", None)
            self.TARGET_PASSWORD = credentials["target"].get("password", None)
            self.TARGET_TOKEN = credentials["target"].get("token", None)

            # Can't fool us that easily
            if self.SOURCE_API_BASE == self.TARGET_API_BASE and (
                (
                    self.SOURCE_USERNAME == self.TARGET_USERNAME
                    and self.SOURCE_PASSWORD == self.TARGET_PASSWORD
                )
                or self.SOURCE_TOKEN == self.TARGET_TOKEN
            ):
                self.IS_PROJECT_IN_SAME_ORG = True
        else:
            self.IS_PROJECT_IN_SAME_ORG = True
            self.TARGET_API_BASE = credentials["source"]["api_base"]
            self.TARGET_USERNAME = credentials["source"].get("username", None)
            self.TARGET_PASSWORD = credentials["source"].get("password", None)
            self.TARGET_TOKEN = credentials["source"].get("token", None)

    IS_PROJECT_IN_SAME_ORG: bool = False

    SOURCE_API_BASE: str = "https://you-forgot-to-cd-into-project.com"
    # Empty string gives an API error even if there is username and password
    SOURCE_TOKEN: str = "dummy_token"
    SOURCE_USERNAME: str = ""
    SOURCE_PASSWORD: str = ""

    MAPPING_FILENAME: str = "mapping.yaml"
    CREDENTIALS_FILENAME: str = "credentials.json"
    MAPPING_KEYS_ORDER: list = ["id", "name", "target_object"]

    TARGET_API_BASE: str = ""
    TARGET_TOKEN: str = "dummy_token"
    TARGET_USERNAME: str = ""
    TARGET_PASSWORD: str = ""

    SOURCE_DIRNAME: str = "source"
    TARGET_DIRNAME: str = "target"

    ORGANIZATION_FIELDS: list[str] = ["ui_settings", "metadata"]
    PRIVATE_HOOK_DUMMY_URL: str = "https://example.com"
    MAPPING_UPPERCASE_FIELDS: list[str] = [
        "organization",
        "workspaces",
        "queues",
        "inbox",
        "schemas",
        "hooks",
    ]

    INITIALIZE_COMMAND_NAME: str = "init"
    DOWNLOAD_COMMAND_NAME: str = "pull"
    UPLOAD_COMMAND_NAME: str = "push"
    MIGRATE_COMMAND_NAME: str = "release"

    IGNORED_KEYS: dict = {"queue": ["counts"]}

    @property
    def SOURCE_API_URL(self):
        return self.SOURCE_API_BASE.rstrip("/")

    @property
    def TARGET_API_URL(self):
        return self.TARGET_API_BASE.rstrip("/")


class GIT_CHARACTERS(StrEnum):
    DELETED = "D"
    UPDATED = "M"
    CREATED = "??"
    CREATED_STAGED = "A"


settings = Settings()

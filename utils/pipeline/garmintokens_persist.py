"""Persist refreshed Garmin OAuth blob to GitHub Actions secrets (CI only)."""

from __future__ import annotations

import logging
import os
import subprocess
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)


def _running_in_github_actions() -> bool:
    return os.getenv("GITHUB_ACTIONS", "").lower() == "true"


def persist_refreshed_garmintokens(blob: str) -> None:
    """Update repo secret GARMINTOKENS when the session blob changed. Never raises."""
    if not _running_in_github_actions():
        return

    blob = blob.strip()
    if not blob.startswith("{") or "di_token" not in blob:
        logger.warning("Skipping GARMINTOKENS persist: exported blob is not DI JSON.")
        return

    current = os.getenv("GARMINTOKENS", "").strip()
    if current == blob:
        logger.info("GARMINTOKENS unchanged after sync; secret update skipped.")
        return

    pat = os.getenv("GH_SECRETS_PAT", "").strip()
    repo = os.getenv("GITHUB_REPOSITORY", "").strip()
    if not pat:
        logger.warning(
            "GH_SECRETS_PAT is not set; cannot write refreshed tokens back. "
            "Create a fine-grained PAT with Actions secrets read/write and add it as "
            "repo secret GH_SECRETS_PAT."
        )
        return
    if not repo:
        logger.warning("GITHUB_REPOSITORY is missing; cannot persist GARMINTOKENS.")
        return

    path: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            delete=False,
            suffix=".json",
        ) as handle:
            handle.write(blob)
            path = handle.name

        env = os.environ.copy()
        env["GH_TOKEN"] = pat
        result = subprocess.run(
            [
                "gh",
                "secret",
                "set",
                "GARMINTOKENS",
                "--repo",
                repo,
                "--body-file",
                path,
            ],
            check=False,
            capture_output=True,
            text=True,
            env=env,
        )
        if result.returncode != 0:
            detail = (result.stderr or result.stdout or "unknown error").strip()
            logger.error("Failed to update GARMINTOKENS secret via gh: %s", detail)
            return
        logger.info("Updated GARMINTOKENS repo secret with refreshed OAuth blob.")
    except FileNotFoundError:
        logger.error("gh CLI not found on runner; cannot persist GARMINTOKENS.")
    except OSError as exc:
        logger.error("Could not persist GARMINTOKENS: %s", exc)
    finally:
        if path:
            Path(path).unlink(missing_ok=True)

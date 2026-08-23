"""Trigger GitHub Actions workflows from the Streamlit app."""

import logging
import os
from dataclasses import dataclass

import requests
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

DEFAULT_REPO = "LucasLherbier/garmin_stats"
WORKFLOW_FILE = "data_extraction_automate.yml"
GITHUB_API_VERSION = "2022-11-28"


@dataclass
class WorkflowDispatchResult:
    ok: bool
    message: str
    workflow_url: str


def _workflow_url() -> str:
    repo = os.getenv("GITHUB_REPO", DEFAULT_REPO).strip()
    return f"https://github.com/{repo}/actions/workflows/{WORKFLOW_FILE}"


def _headers(token: str) -> dict:
    return {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "X-GitHub-Api-Version": GITHUB_API_VERSION,
    }


def trigger_weekly_sync(ref: str | None = None) -> WorkflowDispatchResult:
    """
    Dispatch the Weekly Garmin Sync workflow (workflow_dispatch).

    Requires GITHUB_TOKEN with repo or actions:write scope.
    Optional env: GITHUB_REPO, GITHUB_REF (default main).
    """
    workflow_url = _workflow_url()
    token = os.getenv("GITHUB_TOKEN", "").strip()
    if not token:
        return WorkflowDispatchResult(
            ok=False,
            message="GITHUB_TOKEN is not configured. Add it to your .env or Streamlit secrets.",
            workflow_url=workflow_url,
        )

    repo = os.getenv("GITHUB_REPO", DEFAULT_REPO).strip()
    branch = (ref or os.getenv("GITHUB_REF", "main")).strip()
    url = f"https://api.github.com/repos/{repo}/actions/workflows/{WORKFLOW_FILE}/dispatches"

    try:
        response = requests.post(
            url,
            headers=_headers(token),
            json={"ref": branch},
            timeout=30,
        )
    except requests.RequestException as exc:
        logger.exception("GitHub workflow dispatch failed")
        return WorkflowDispatchResult(
            ok=False,
            message=f"Could not reach GitHub: {exc}",
            workflow_url=workflow_url,
        )

    if response.status_code == 204:
        return WorkflowDispatchResult(
            ok=True,
            message=f"Weekly sync started on branch `{branch}`.",
            workflow_url=workflow_url,
        )

    detail = response.text.strip() or response.reason
    if response.status_code == 401:
        message = "GitHub rejected the token (401). Check GITHUB_TOKEN permissions."
    elif response.status_code == 404:
        message = f"Workflow or repo not found (404). Verify GITHUB_REPO={repo!r}."
    elif response.status_code == 422:
        message = f"GitHub could not start the workflow on `{branch}` (422). Check GITHUB_REF."
    else:
        message = f"GitHub returned {response.status_code}: {detail}"

    return WorkflowDispatchResult(ok=False, message=message, workflow_url=workflow_url)

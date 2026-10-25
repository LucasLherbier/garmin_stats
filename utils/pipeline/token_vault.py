"""Single-user encrypted Garmin token vault backed by GCS.

Endurain-style writable token store, simplified for one user (no password,
no MFA linking needed): the DI token blob is Fernet-encrypted and stored at
``tokens/garmin_tokens.json.enc`` in the GCS bucket.

- On first run (no vault object yet) it falls back to the GARMINTOKENS env
  var, so migration is zero-touch: set TOKEN_VAULT_KEY (+ GARMINTOKENS once
  on the host) and deploy.
- After every successful sync the refreshed blob is written back, so the
  token store never goes stale the way the static GitHub secret did.

Required env: TOKEN_VAULT_KEY — generate once with:
    python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

from dotenv import load_dotenv

_REPO_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(_REPO_ROOT / ".env")

logger = logging.getLogger(__name__)

VAULT_GCS_PATH = (
    os.getenv("TOKEN_VAULT_GCS_PATH", "tokens/garmin_tokens.json.enc").strip('"').strip("'")
)


def _fernet():
    from cryptography.fernet import Fernet

    key = os.getenv("TOKEN_VAULT_KEY", "").strip().strip('"').strip("'")
    if not key:
        raise RuntimeError(
            "TOKEN_VAULT_KEY is not set. Generate one with: "
            'python -c "from cryptography.fernet import Fernet; '
            'print(Fernet.generate_key().decode())"'
        )
    return Fernet(key.encode())


def load_token_blob() -> str | None:
    """Return the DI token blob: GCS vault first, GARMINTOKENS env as fallback."""
    try:
        import utils.utils_gcp as gcp

        if gcp.bucket is not None:
            blob = gcp.bucket.blob(VAULT_GCS_PATH)
            if blob.exists():
                decrypted = _fernet().decrypt(blob.download_as_bytes()).decode("utf-8")
                logger.info("Loaded Garmin tokens from GCS vault.")
                return decrypted
            logger.info("No vault object at %s; trying GARMINTOKENS env.", VAULT_GCS_PATH)
    except Exception as exc:
        logger.warning("Could not read token vault from GCS: %s", exc)

    env_blob = os.getenv("GARMINTOKENS", "").strip()
    if env_blob:
        logger.info("Using GARMINTOKENS env var for Garmin login (first-run migration).")
        return env_blob
    logger.error("No Garmin tokens found (vault empty and GARMINTOKENS unset).")
    return None


def save_token_blob(token_blob: str) -> bool:
    """Encrypt and persist the refreshed blob to the GCS vault. Returns success."""
    try:
        import utils.utils_gcp as gcp

        if gcp.bucket is None:
            logger.error("GCS bucket not initialized; cannot save token vault.")
            return False
        encrypted = _fernet().encrypt(token_blob.encode("utf-8"))
        gcp.bucket.blob(VAULT_GCS_PATH).upload_from_string(
            encrypted, content_type="application/octet-stream"
        )
        logger.info("Saved refreshed Garmin tokens to GCS vault.")
        return True
    except Exception as exc:
        logger.error("Could not save token vault to GCS: %s", exc)
        return False

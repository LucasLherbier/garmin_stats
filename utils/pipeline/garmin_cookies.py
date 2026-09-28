import logging
import os
import time
from pathlib import Path

from dotenv import load_dotenv
from garminconnect import Garmin

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

_REPO_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_TOKEN_DIR = _REPO_ROOT / ".garmin_tokens"
_LOGIN_RETRIES = 5


def _token_dir() -> Path:
    raw = os.getenv("GARMINTOKENS", "").strip()
    if raw and len(raw) <= 512:
        expanded = Path(os.path.expanduser(raw))
        if expanded.is_dir():
            return expanded
    return _DEFAULT_TOKEN_DIR


def _env_token_blob() -> str:
    """Inline OAuth payload (garth.dumps) for CI secrets."""
    raw = os.getenv("GARMINTOKENS", "").strip()
    if raw and len(raw) > 512:
        return raw
    return ""


def _tokens_present(token_dir: Path) -> bool:
    return (token_dir / "oauth1_token.json").is_file() and (
        token_dir / "oauth2_token.json"
    ).is_file()


def _rate_limited(exc: Exception) -> bool:
    text = str(exc).lower()
    return "429" in text or "rate limit" in text


def _login_with_retry(client: Garmin, *, tokenstore: str | None = None) -> None:
    last_exc: Exception | None = None
    for attempt in range(_LOGIN_RETRIES):
        try:
            client.login(tokenstore=tokenstore)
            return
        except Exception as exc:
            last_exc = exc
            if not _rate_limited(exc) or attempt >= _LOGIN_RETRIES - 1:
                raise
            wait = min(300, 60 * (attempt + 1))
            logger.warning(
                "Garmin login rate-limited; retry %s/%s in %ss",
                attempt + 1,
                _LOGIN_RETRIES - 1,
                wait,
            )
            time.sleep(wait)
    if last_exc:
        raise last_exc


def _save_tokens(client: Garmin, token_dir: Path) -> None:
    garth_client = getattr(client, "garth", None)
    if garth_client is None or not hasattr(garth_client, "dump"):
        logger.warning("Garmin client has no garth store; skipping token save.")
        return
    token_dir.mkdir(parents=True, exist_ok=True)
    garth_client.dump(str(token_dir))
    logger.info("Saved Garmin tokens to %s", token_dir)


def get_garmin_client(email, password):
    token_dir = _token_dir()
    client = Garmin(email, password)

    if _env_token_blob():
        try:
            _login_with_retry(client)
            logger.info("Logged in to Garmin Connect using GARMINTOKENS env")
            return client
        except Exception as exc:
            logger.warning("GARMINTOKENS env login failed (%s).", exc)

    if _tokens_present(token_dir):
        try:
            _login_with_retry(client, tokenstore=str(token_dir))
            logger.info("Logged in to Garmin Connect using saved tokens (%s)", token_dir)
            return client
        except Exception as exc:
            logger.warning("Saved tokens unusable (%s); trying password login.", exc)

    if not email or not password:
        logger.error(
            "Garmin login requires USER_EMAIL/USER_PASSWORD or valid GARMINTOKENS / %s",
            token_dir,
        )
        return None

    try:
        _login_with_retry(client)
        _save_tokens(client, token_dir)
        logger.info("Logged in to Garmin Connect with password")
        return client
    except Exception as e:
        logger.error("Failed to login to Garmin Connect: %s", e)
        return None


def load_credentials():
    load_dotenv(_REPO_ROOT / ".env")
    email = os.getenv("USER_EMAIL")
    password = os.getenv("USER_PASSWORD")
    if not email or not password:
        if _env_token_blob() or _tokens_present(_token_dir()):
            return None, None
        logger.error("USER_EMAIL or USER_PASSWORD environment variables not found.")
        return None, None
    return email, password


def main():
    email, password = load_credentials()
    return get_garmin_client(email, password)

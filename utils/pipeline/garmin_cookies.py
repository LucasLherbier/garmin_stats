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
    return Path(os.path.expanduser(raw)) if raw else _DEFAULT_TOKEN_DIR


def _tokens_present(token_dir: Path) -> bool:
    return (token_dir / "oauth1_token.json").is_file() and (
        token_dir / "oauth2_token.json"
    ).is_file()


def _login_with_retry(client: Garmin, *, tokenstore: str | None = None) -> None:
    last_exc: Exception | None = None
    for attempt in range(_LOGIN_RETRIES):
        try:
            client.login(tokenstore=tokenstore)
            return
        except Exception as exc:
            last_exc = exc
            if "429" not in str(exc) or attempt >= _LOGIN_RETRIES - 1:
                raise
            wait = min(300, 60 * (attempt + 1))
            logger.warning(
                "Garmin SSO rate-limited (429); retry %s/%s in %ss",
                attempt + 1,
                _LOGIN_RETRIES - 1,
                wait,
            )
            time.sleep(wait)
    if last_exc:
        raise last_exc


def get_garmin_client(email, password):
    token_dir = _token_dir()
    client = Garmin(email, password)

    if _tokens_present(token_dir):
        try:
            _login_with_retry(client, tokenstore=str(token_dir))
            logger.info("Logged in to Garmin Connect using saved tokens (%s)", token_dir)
            return client
        except Exception as exc:
            logger.warning("Saved tokens unusable (%s); trying password login.", exc)

    try:
        _login_with_retry(client)
        token_dir.mkdir(parents=True, exist_ok=True)
        client.garth.dump(str(token_dir))
        logger.info("Logged in to Garmin Connect; tokens saved to %s", token_dir)
        return client
    except Exception as e:
        logger.error(f"Failed to login to Garmin Connect: {e}")
        return None


def load_credentials():
    load_dotenv(_REPO_ROOT / ".env")
    email = os.getenv("USER_EMAIL")
    password = os.getenv("USER_PASSWORD")
    if not email or not password:
        logger.error("USER_EMAIL or USER_PASSWORD environment variables not found.")
        return None, None
    return email, password


def main():
    email, password = load_credentials()
    if email and password:
        return get_garmin_client(email, password)
    return None

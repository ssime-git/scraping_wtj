from __future__ import annotations

import asyncio
import os
import tempfile
from pathlib import Path

from wttj_scraper.browser import browser_context
from wttj_scraper.config import load_matches_config
from wttj_scraper.logging_utils import configure_logger
from wttj_scraper.matches_auth import login_to_matches

CONFIG_PATH = os.getenv("WTTJ_MATCHES_CONFIG", "config/wttj_matches.yaml")
AUTH_STATE_PATH = Path(
    os.getenv("WTTJ_AUTH_STATE_PATH", str(Path.home() / ".local/state/wttj-scrape/auth-state.json")),
)


async def main() -> None:
    config = load_matches_config(CONFIG_PATH)
    logger = configure_logger()
    profile_root = Path(os.getenv("WTTJ_PROFILE_DIR", str(Path.home() / ".local/state/wttj-scrape/profile")))
    profile_root.mkdir(parents=True, exist_ok=True)

    last_error: Exception | None = None
    for attempt in range(1, 4):
        with tempfile.TemporaryDirectory(prefix="wttj-auth-", dir=str(profile_root.parent)) as temp_profile:
            try:
                async with browser_context(profile_dir=Path(temp_profile)) as context:
                    page = await login_to_matches(
                        context=context,
                        login_url=config.auth.login_url,
                        matches_url=config.auth.matches_url,
                        email=config.auth.email,
                        password=config.auth.password,
                        logger=logger,
                        auth_state_path=AUTH_STATE_PATH,
                    )
                    await page.close()
                print(f"Refreshed WTTJ auth state at {AUTH_STATE_PATH}")
                return
            except Exception as exc:
                last_error = exc
                logger.warning("Auth refresh attempt %s failed: %s", attempt, exc)
                await asyncio.sleep(5 * attempt)

    assert last_error is not None
    raise last_error


if __name__ == "__main__":
    asyncio.run(main())

"""hCaptcha verification for public forms (waitlist, signup)."""

from __future__ import annotations

import httpx

HCAPTCHA_VERIFY_URL = "https://api.hcaptcha.com/siteverify"


async def verify_hcaptcha(
    token: str,
    *,
    secret: str | None = None,
    sitekey: str | None = None,
) -> bool:
    if secret is None:
        return True

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            data = {"response": token, "secret": secret}
            if sitekey:
                data["sitekey"] = sitekey
            resp = await client.post(HCAPTCHA_VERIFY_URL, data=data)
            resp.raise_for_status()
            return resp.json().get("success", False)
    except httpx.HTTPError:
        return False

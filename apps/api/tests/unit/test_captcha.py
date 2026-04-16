"""hCaptcha verification tests."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from dailyriff_api.services.captcha import verify_hcaptcha


class TestVerifyHCaptcha:
    @pytest.mark.asyncio
    async def test_valid_token_returns_true(self) -> None:
        mock_response = AsyncMock()
        mock_response.json = lambda: {"success": True}
        mock_response.raise_for_status = lambda: None

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("dailyriff_api.services.captcha.httpx.AsyncClient", return_value=mock_client):
            result = await verify_hcaptcha("valid-token", secret="test-secret")

        assert result is True

    @pytest.mark.asyncio
    async def test_invalid_token_returns_false(self) -> None:
        mock_response = AsyncMock()
        mock_response.json = lambda: {"success": False}
        mock_response.raise_for_status = lambda: None

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("dailyriff_api.services.captcha.httpx.AsyncClient", return_value=mock_client):
            result = await verify_hcaptcha("invalid-token", secret="test-secret")

        assert result is False

    @pytest.mark.asyncio
    async def test_network_error_returns_false(self) -> None:
        import httpx

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=httpx.HTTPError("connection failed"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("dailyriff_api.services.captcha.httpx.AsyncClient", return_value=mock_client):
            result = await verify_hcaptcha("some-token", secret="test-secret")

        assert result is False

    @pytest.mark.asyncio
    async def test_skips_verification_when_no_secret(self) -> None:
        result = await verify_hcaptcha("any-token", secret=None)
        assert result is True

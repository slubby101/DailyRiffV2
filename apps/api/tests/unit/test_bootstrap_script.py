"""Bootstrap script unit tests — sanity checks."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, patch

import pytest

from tests.conftest import USER_A_ID


class TestBootstrapFirstOwner:
    @pytest.mark.asyncio
    async def test_aborts_when_employees_exist(self) -> None:
        from dailyriff_api.scripts.bootstrap_first_owner import _run

        mock_conn = AsyncMock()
        mock_conn.fetchval = AsyncMock(return_value=1)  # 1 employee exists
        mock_conn.close = AsyncMock()

        with patch("dailyriff_api.scripts.bootstrap_first_owner.asyncpg") as mock_pg:
            mock_pg.connect = AsyncMock(return_value=mock_conn)
            with pytest.raises(SystemExit) as exc_info:
                await _run(USER_A_ID, dry_run=True)
            assert exc_info.value.code == 1

    @pytest.mark.asyncio
    async def test_aborts_when_user_not_found(self) -> None:
        from dailyriff_api.scripts.bootstrap_first_owner import _run

        mock_conn = AsyncMock()
        mock_conn.fetchval = AsyncMock(return_value=0)  # no employees
        mock_conn.fetchrow = AsyncMock(return_value=None)  # user not found
        mock_conn.close = AsyncMock()

        with patch("dailyriff_api.scripts.bootstrap_first_owner.asyncpg") as mock_pg:
            mock_pg.connect = AsyncMock(return_value=mock_conn)
            with pytest.raises(SystemExit) as exc_info:
                await _run(USER_A_ID, dry_run=True)
            assert exc_info.value.code == 1

    @pytest.mark.asyncio
    async def test_dry_run_succeeds_without_inserting(self, monkeypatch) -> None:
        from dailyriff_api.scripts.bootstrap_first_owner import _run

        monkeypatch.setenv("ENVIRONMENT", "development")

        mock_conn = AsyncMock()
        mock_conn.fetchval = AsyncMock(return_value=0)  # no employees
        mock_conn.fetchrow = AsyncMock(
            return_value={"id": USER_A_ID, "email": "test@dailyriff.local"}
        )
        mock_conn.execute = AsyncMock()
        mock_conn.close = AsyncMock()

        with patch("dailyriff_api.scripts.bootstrap_first_owner.asyncpg") as mock_pg:
            mock_pg.connect = AsyncMock(return_value=mock_conn)
            await _run(USER_A_ID, dry_run=True)

        # execute should NOT have been called (dry run)
        mock_conn.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_inserts_owner_when_checks_pass(self, monkeypatch) -> None:
        from dailyriff_api.scripts.bootstrap_first_owner import _run

        monkeypatch.setenv("ENVIRONMENT", "development")

        mock_conn = AsyncMock()
        mock_conn.fetchval = AsyncMock(return_value=0)  # no employees
        mock_conn.fetchrow = AsyncMock(
            return_value={"id": USER_A_ID, "email": "test@dailyriff.local"}
        )
        mock_conn.execute = AsyncMock()
        mock_conn.close = AsyncMock()

        with patch("dailyriff_api.scripts.bootstrap_first_owner.asyncpg") as mock_pg:
            mock_pg.connect = AsyncMock(return_value=mock_conn)
            await _run(USER_A_ID, dry_run=False)

        mock_conn.execute.assert_called_once()
        call_args = mock_conn.execute.call_args
        assert "INSERT INTO dailyriff_employees" in call_args[0][0]
        assert call_args[0][1] == USER_A_ID

    @pytest.mark.asyncio
    async def test_production_aborts_without_totp(self, monkeypatch) -> None:
        from dailyriff_api.scripts.bootstrap_first_owner import _run

        monkeypatch.setenv("ENVIRONMENT", "production")

        mock_conn = AsyncMock()
        # First fetchval returns 0 (no employees), second returns 0 (no TOTP)
        mock_conn.fetchval = AsyncMock(side_effect=[0, 0])
        mock_conn.fetchrow = AsyncMock(
            return_value={"id": USER_A_ID, "email": "test@dailyriff.local"}
        )
        mock_conn.close = AsyncMock()

        with patch("dailyriff_api.scripts.bootstrap_first_owner.asyncpg") as mock_pg:
            mock_pg.connect = AsyncMock(return_value=mock_conn)
            with pytest.raises(SystemExit) as exc_info:
                await _run(USER_A_ID, dry_run=True)
            assert exc_info.value.code == 1

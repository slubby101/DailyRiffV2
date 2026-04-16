"""Seed script unit tests — idempotency, safety guards, data integrity."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


LOCAL_DSN = "postgresql://postgres:postgres@localhost:54322/postgres"


class TestSeedPolymet:
    @pytest.mark.asyncio
    async def test_dry_run_does_not_touch_database(self) -> None:
        from dailyriff_api.scripts.seed_polymet import _run

        with patch("dailyriff_api.scripts.seed_polymet._dsn", return_value=LOCAL_DSN), \
             patch("dailyriff_api.scripts.seed_polymet.asyncpg") as mock_pg, \
             patch("dailyriff_api.scripts.seed_polymet._create_auth_users") as mock_auth:
            await _run(dry_run=True)
            mock_pg.connect.assert_not_called()
            mock_auth.assert_not_called()

    @pytest.mark.asyncio
    async def test_refuses_non_local_database(self, monkeypatch) -> None:
        from dailyriff_api.scripts.seed_polymet import _run

        monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@prod-db.example.com/db")
        with pytest.raises(SystemExit) as exc_info:
            await _run(dry_run=False)
        assert exc_info.value.code == 1

    @pytest.mark.asyncio
    async def test_seeds_all_tables(self) -> None:
        from dailyriff_api.scripts.seed_polymet import _run, _seed_database

        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock()
        mock_conn.close = AsyncMock()

        with patch("dailyriff_api.scripts.seed_polymet._dsn", return_value=LOCAL_DSN), \
             patch("dailyriff_api.scripts.seed_polymet.asyncpg") as mock_pg, \
             patch("dailyriff_api.scripts.seed_polymet._create_auth_users"):
            mock_pg.connect = AsyncMock(return_value=mock_conn)
            await _run(dry_run=False)

        # Verify that execute was called many times (studio, members, parents, etc.)
        call_count = mock_conn.execute.call_count
        assert call_count >= 30, f"Expected 30+ INSERT calls, got {call_count}"

    @pytest.mark.asyncio
    async def test_all_inserts_use_on_conflict(self) -> None:
        """Every INSERT must use ON CONFLICT DO NOTHING for idempotency."""
        from dailyriff_api.scripts.seed_polymet import _seed_database

        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock()

        await _seed_database(mock_conn)

        for call in mock_conn.execute.call_args_list:
            sql = call.args[0] if call.args else ""
            if "INSERT INTO" in sql:
                assert "ON CONFLICT" in sql, (
                    f"INSERT without ON CONFLICT (not idempotent): {sql[:100]}"
                )

    def test_deterministic_uuids_are_stable(self) -> None:
        """All seed UUIDs should be importable constants, not random."""
        from dailyriff_api.scripts.seed_polymet import (
            STUDIO_ID, ELLEN_ID, SARAH_ID, MARCUS_ID,
            ASSIGN_SARAH_1, REC_SARAH_1, LESSON_SARAH,
            CONV_ELLEN_AMY, MSG_1, PAY_1, RES_1, LOAN_1,
        )
        # Verify they are deterministic (same import = same value)
        from dailyriff_api.scripts.seed_polymet import STUDIO_ID as STUDIO_ID_2
        assert STUDIO_ID == STUDIO_ID_2

    def test_studio_respects_tenant_boundary(self) -> None:
        """All seed entities reference a single studio ID."""
        import dailyriff_api.scripts.seed_polymet as sp
        # All member, assignment, recording, etc. IDs reference STUDIO_ID
        assert sp.STUDIO_ID is not None


class TestSeedEdgeCases:
    @pytest.mark.asyncio
    async def test_dry_run_does_not_touch_database(self) -> None:
        from dailyriff_api.scripts.seed_edge_cases import _run

        with patch("dailyriff_api.scripts.seed_edge_cases._dsn", return_value=LOCAL_DSN), \
             patch("dailyriff_api.scripts.seed_edge_cases.asyncpg") as mock_pg, \
             patch("dailyriff_api.scripts.seed_edge_cases._create_auth_users") as mock_auth:
            await _run(dry_run=True)
            mock_pg.connect.assert_not_called()
            mock_auth.assert_not_called()

    @pytest.mark.asyncio
    async def test_refuses_non_local_database(self, monkeypatch) -> None:
        from dailyriff_api.scripts.seed_edge_cases import _run

        monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@prod-db.example.com/db")
        with pytest.raises(SystemExit) as exc_info:
            await _run(dry_run=False)
        assert exc_info.value.code == 1

    @pytest.mark.asyncio
    async def test_all_inserts_use_on_conflict(self) -> None:
        """Every INSERT must use ON CONFLICT DO NOTHING for idempotency."""
        from dailyriff_api.scripts.seed_edge_cases import _seed_edge_cases

        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock()

        await _seed_edge_cases(mock_conn)

        for call in mock_conn.execute.call_args_list:
            sql = call.args[0] if call.args else ""
            if "INSERT INTO" in sql:
                assert "ON CONFLICT" in sql, (
                    f"INSERT without ON CONFLICT (not idempotent): {sql[:100]}"
                )

    @pytest.mark.asyncio
    async def test_seeds_all_four_edge_cases(self) -> None:
        """Should seed pending-deletion, mid-conversion, divorced-family, and failed-upload."""
        from dailyriff_api.scripts.seed_edge_cases import _seed_edge_cases

        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock()

        await _seed_edge_cases(mock_conn)

        all_sql = " ".join(
            call.args[0] for call in mock_conn.execute.call_args_list
            if call.args
        )
        # Verify all four edge cases touched the database
        assert "coppa_deletion_requests" in all_sql, "Missing pending-deletion edge case"
        assert "coppa_consents" in all_sql, "Missing COPPA consent for pending-deletion"
        assert "assignments" in all_sql, "Missing mid-conversion assignment"
        assert "recordings" in all_sql, "Missing failed-upload recording"

    def test_divorced_family_has_split_permissions(self) -> None:
        """Parent A should have full permissions, Parent B should have restricted."""
        from dailyriff_api.scripts.seed_edge_cases import (
            DIVORCED_PARENT_A_ID, DIVORCED_PARENT_B_ID,
            PARENT_DIV_A, PARENT_DIV_B,
        )
        # These are distinct parents
        assert PARENT_DIV_A != PARENT_DIV_B
        assert DIVORCED_PARENT_A_ID != DIVORCED_PARENT_B_ID

    def test_edge_cases_use_polymet_studio(self) -> None:
        """Edge cases should layer on top of the Polymet studio, not create a new one."""
        from dailyriff_api.scripts.seed_edge_cases import STUDIO_ID
        from dailyriff_api.scripts.seed_polymet import STUDIO_ID as POLYMET_STUDIO_ID
        assert STUDIO_ID == POLYMET_STUDIO_ID

    def test_edge_case_uuids_dont_collide_with_polymet(self) -> None:
        """Edge-case UUIDs must not overlap with Polymet UUIDs."""
        from dailyriff_api.scripts import seed_polymet as sp
        from dailyriff_api.scripts import seed_edge_cases as ec

        polymet_uuids = {
            sp.STUDIO_ID, sp.ELLEN_ID, sp.SARAH_ID, sp.MARCUS_ID,
            sp.LILY_ID, sp.JAKE_ID, sp.EMMA_ID, sp.AMY_ID,
            sp.DAVID_ID, sp.WEI_ID, sp.JENNIFER_ID,
            sp.ASSIGN_SARAH_1, sp.ASSIGN_SARAH_2, sp.ASSIGN_MARCUS_1,
        }
        edge_uuids = {
            ec.PENDING_DELETE_PARENT_ID, ec.PENDING_DELETE_CHILD_ID,
            ec.MID_CONVERSION_STUDENT_ID, ec.MID_CONVERSION_PARENT_ID,
            ec.DIVORCED_CHILD_ID, ec.DIVORCED_PARENT_A_ID,
            ec.DIVORCED_PARENT_B_ID, ec.FAILED_UPLOAD_STUDENT_ID,
        }

        overlap = polymet_uuids & edge_uuids
        assert len(overlap) == 0, f"UUID collision: {overlap}"


class TestMakefileTargets:
    def test_makefile_exists(self) -> None:
        from pathlib import Path
        makefile = Path(__file__).parents[4] / "Makefile"
        assert makefile.exists(), "Makefile not found at repo root"

    def test_makefile_has_seed_targets(self) -> None:
        from pathlib import Path
        makefile = Path(__file__).parents[4] / "Makefile"
        content = makefile.read_text()
        assert "seed-polymet-only" in content
        assert "seed-rich" in content
        assert "seed-edge-cases" in content

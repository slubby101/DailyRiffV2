"""COPPA deletion service unit tests — TDD red-green-refactor."""

from __future__ import annotations

import hashlib
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from typing import Any
from unittest.mock import AsyncMock

import pytest

from tests.conftest import USER_A_ID

PARENT_ID = uuid.UUID("aaaaaaaa-0000-0000-0000-000000000001")
CHILD_ID = uuid.UUID("cccccccc-0000-0000-0000-000000000001")
STUDIO_ID = uuid.UUID("dddddddd-0000-0000-0000-000000000001")
NOW = datetime.now(timezone.utc)


def _make_conn(*, fetchrow_result=None, fetchval_result=None, execute_result="UPDATE 1"):
    conn = AsyncMock()
    conn.fetchrow = AsyncMock(return_value=fetchrow_result)
    conn.fetchval = AsyncMock(return_value=fetchval_result)
    conn.execute = AsyncMock(return_value=execute_result)
    conn.fetch = AsyncMock(return_value=[])
    return conn


# ---- Test 1: initiate_deletion creates a pending request ----

@pytest.mark.asyncio
async def test_initiate_deletion_creates_pending_request():
    from dailyriff_api.services.coppa_deletion_service import CoppaDeletionService

    request_id = uuid.uuid4()
    token = "test-confirmation-token"
    conn = _make_conn(fetchrow_result={
        "id": request_id,
        "parent_id": PARENT_ID,
        "child_id": CHILD_ID,
        "studio_id": STUDIO_ID,
        "status": "pending_confirmation",
        "confirmation_token_hash": hashlib.sha256(token.encode()).hexdigest(),
        "email_confirmed_at": None,
        "scheduled_delete_at": None,
        "created_at": NOW,
        "updated_at": NOW,
    })

    result = await CoppaDeletionService.initiate_deletion(
        conn=conn,
        parent_id=PARENT_ID,
        child_id=CHILD_ID,
        studio_id=STUDIO_ID,
    )

    assert result["status"] == "pending_confirmation"
    assert result["id"] == request_id
    # Token is returned plaintext for inclusion in confirmation email
    assert "confirmation_token" in result
    conn.fetchrow.assert_called_once()


# ---- Test 2: confirm_deletion with valid token schedules hard-delete ----

@pytest.mark.asyncio
async def test_confirm_deletion_with_valid_token_schedules():
    from dailyriff_api.services.coppa_deletion_service import CoppaDeletionService

    request_id = uuid.uuid4()
    token = "the-real-confirmation-token"
    token_hash = hashlib.sha256(token.encode()).hexdigest()

    pending_row = {
        "id": request_id,
        "parent_id": PARENT_ID,
        "child_id": CHILD_ID,
        "studio_id": STUDIO_ID,
        "status": "pending_confirmation",
        "confirmation_token_hash": token_hash,
        "email_confirmed_at": None,
        "scheduled_delete_at": None,
        "created_at": NOW,
        "updated_at": NOW,
    }

    confirmed_row = {
        **pending_row,
        "status": "scheduled",
        "email_confirmed_at": NOW,
        "scheduled_delete_at": NOW + timedelta(days=15),
    }

    conn = _make_conn()
    conn.fetchrow = AsyncMock(side_effect=[pending_row, confirmed_row])

    result = await CoppaDeletionService.confirm_deletion(
        conn=conn,
        request_id=request_id,
        confirmation_token=token,
        parent_id=PARENT_ID,
        grace_days=15,
    )

    assert result is not None
    assert result["status"] == "scheduled"
    assert result["email_confirmed_at"] is not None
    assert result["scheduled_delete_at"] is not None


# ---- Test 3: confirm_deletion with wrong token returns None ----

@pytest.mark.asyncio
async def test_confirm_deletion_with_wrong_token_returns_none():
    from dailyriff_api.services.coppa_deletion_service import CoppaDeletionService

    request_id = uuid.uuid4()
    real_token = "correct-token"
    token_hash = hashlib.sha256(real_token.encode()).hexdigest()

    pending_row = {
        "id": request_id,
        "parent_id": PARENT_ID,
        "child_id": CHILD_ID,
        "studio_id": STUDIO_ID,
        "status": "pending_confirmation",
        "confirmation_token_hash": token_hash,
        "email_confirmed_at": None,
        "scheduled_delete_at": None,
        "created_at": NOW,
        "updated_at": NOW,
    }

    conn = _make_conn(fetchrow_result=pending_row)

    result = await CoppaDeletionService.confirm_deletion(
        conn=conn,
        request_id=request_id,
        confirmation_token="wrong-token",
        parent_id=PARENT_ID,
    )

    assert result is None


# ---- Test 4: cancel_deletion cancels a scheduled request ----

@pytest.mark.asyncio
async def test_cancel_deletion_cancels_scheduled_request():
    from dailyriff_api.services.coppa_deletion_service import CoppaDeletionService

    request_id = uuid.uuid4()
    scheduled_row = {
        "id": request_id,
        "parent_id": PARENT_ID,
        "child_id": CHILD_ID,
        "studio_id": STUDIO_ID,
        "status": "scheduled",
        "confirmation_token_hash": "hash",
        "email_confirmed_at": NOW,
        "scheduled_delete_at": NOW + timedelta(days=10),
        "created_at": NOW,
        "updated_at": NOW,
    }

    cancelled_row = {**scheduled_row, "status": "cancelled", "cancelled_at": NOW}
    conn = _make_conn()
    conn.fetchrow = AsyncMock(side_effect=[scheduled_row, cancelled_row])

    result = await CoppaDeletionService.cancel_deletion(
        conn=conn,
        request_id=request_id,
        parent_id=PARENT_ID,
    )

    assert result is not None
    assert result["status"] == "cancelled"


# ---- Test 5: cancel_deletion on completed request returns None ----

@pytest.mark.asyncio
async def test_cancel_deletion_on_completed_returns_none():
    from dailyriff_api.services.coppa_deletion_service import CoppaDeletionService

    request_id = uuid.uuid4()
    completed_row = {
        "id": request_id,
        "parent_id": PARENT_ID,
        "child_id": CHILD_ID,
        "studio_id": STUDIO_ID,
        "status": "completed",
        "confirmation_token_hash": "hash",
        "email_confirmed_at": NOW,
        "scheduled_delete_at": NOW - timedelta(days=1),
        "completed_at": NOW,
        "created_at": NOW,
        "updated_at": NOW,
    }

    conn = _make_conn(fetchrow_result=completed_row)

    result = await CoppaDeletionService.cancel_deletion(
        conn=conn,
        request_id=request_id,
        parent_id=PARENT_ID,
    )

    assert result is None


# ---- Test 6: cancel_deletion by wrong parent returns None ----

@pytest.mark.asyncio
async def test_cancel_deletion_wrong_parent_returns_none():
    from dailyriff_api.services.coppa_deletion_service import CoppaDeletionService

    request_id = uuid.uuid4()
    conn = _make_conn(fetchrow_result=None)

    result = await CoppaDeletionService.cancel_deletion(
        conn=conn,
        request_id=request_id,
        parent_id=uuid.uuid4(),
    )

    assert result is None


# ---- Test 7: get_deletion_status returns active request ----

@pytest.mark.asyncio
async def test_get_deletion_status_returns_active_request():
    from dailyriff_api.services.coppa_deletion_service import CoppaDeletionService

    request_id = uuid.uuid4()
    active_row = {
        "id": request_id,
        "parent_id": PARENT_ID,
        "child_id": CHILD_ID,
        "studio_id": STUDIO_ID,
        "status": "scheduled",
        "confirmation_token_hash": "hash",
        "email_confirmed_at": NOW,
        "scheduled_delete_at": NOW + timedelta(days=5),
        "created_at": NOW,
        "updated_at": NOW,
    }

    conn = _make_conn(fetchrow_result=active_row)

    result = await CoppaDeletionService.get_deletion_status(
        conn=conn,
        parent_id=PARENT_ID,
        child_id=CHILD_ID,
        studio_id=STUDIO_ID,
    )

    assert result is not None
    assert result["status"] == "scheduled"


# ---- Test 8: get_deletion_status returns None when no active request ----

@pytest.mark.asyncio
async def test_get_deletion_status_returns_none_when_no_active():
    from dailyriff_api.services.coppa_deletion_service import CoppaDeletionService

    conn = _make_conn(fetchrow_result=None)

    result = await CoppaDeletionService.get_deletion_status(
        conn=conn,
        parent_id=PARENT_ID,
        child_id=CHILD_ID,
        studio_id=STUDIO_ID,
    )

    assert result is None


# ---- Test 9: hard delete worker calls SQL function ----

@pytest.mark.asyncio
async def test_hard_delete_worker_calls_sql_function():
    from dailyriff_api.services.coppa_deletion_service import CoppaDeletionService

    conn = _make_conn(fetchval_result=3)

    result = await CoppaDeletionService.run_hard_delete_worker(conn=conn)

    assert result == 3
    conn.fetchval.assert_called_once_with("SELECT public.coppa_hard_delete_worker()")


# ---- Test 10: cancel at pending_confirmation stage works ----

@pytest.mark.asyncio
async def test_cancel_deletion_at_pending_confirmation_works():
    from dailyriff_api.services.coppa_deletion_service import CoppaDeletionService

    request_id = uuid.uuid4()
    pending_row = {
        "id": request_id,
        "parent_id": PARENT_ID,
        "child_id": CHILD_ID,
        "studio_id": STUDIO_ID,
        "status": "pending_confirmation",
        "confirmation_token_hash": "hash",
        "email_confirmed_at": None,
        "scheduled_delete_at": None,
        "created_at": NOW,
        "updated_at": NOW,
    }

    cancelled_row = {**pending_row, "status": "cancelled", "cancelled_at": NOW}
    conn = _make_conn()
    conn.fetchrow = AsyncMock(side_effect=[pending_row, cancelled_row])

    result = await CoppaDeletionService.cancel_deletion(
        conn=conn,
        request_id=request_id,
        parent_id=PARENT_ID,
    )

    assert result is not None
    assert result["status"] == "cancelled"


# ---- Test 11: confirm on already-confirmed request returns None ----

@pytest.mark.asyncio
async def test_confirm_on_already_scheduled_returns_none():
    from dailyriff_api.services.coppa_deletion_service import CoppaDeletionService

    request_id = uuid.uuid4()
    scheduled_row = {
        "id": request_id,
        "parent_id": PARENT_ID,
        "child_id": CHILD_ID,
        "studio_id": STUDIO_ID,
        "status": "scheduled",
        "confirmation_token_hash": "hash",
        "email_confirmed_at": NOW,
        "scheduled_delete_at": NOW + timedelta(days=10),
        "created_at": NOW,
        "updated_at": NOW,
    }

    conn = _make_conn(fetchrow_result=scheduled_row)

    result = await CoppaDeletionService.confirm_deletion(
        conn=conn,
        request_id=request_id,
        confirmation_token="any",
        parent_id=PARENT_ID,
    )

    assert result is None

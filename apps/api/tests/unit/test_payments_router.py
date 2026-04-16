"""Payments router unit tests with mocked DB."""

from __future__ import annotations

import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from decimal import Decimal
from typing import Callable
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from dailyriff_api.main import app
from tests.conftest import USER_A_ID, USER_B_ID

NOW = datetime.now(timezone.utc)
STUDIO_ID = uuid.uuid4()
STUDENT_USER_ID = uuid.uuid4()
PAYMENT_ID = uuid.uuid4()

TEACHER_MEMBERSHIP = {"role": "teacher"}
STUDENT_MEMBERSHIP = {"role": "student"}

PAYMENT_ROW = {
    "id": PAYMENT_ID,
    "studio_id": STUDIO_ID,
    "student_user_id": STUDENT_USER_ID,
    "amount": Decimal("50.00"),
    "currency": "USD",
    "payer_user_id": None,
    "status": "pending",
    "method": "cash",
    "memo": "March lesson fee",
    "refunded_at": None,
    "created_by": USER_A_ID,
    "created_at": NOW,
    "updated_at": NOW,
}


def _make_service_ctx(
    *,
    fetchrow_results=None,
    fetch_results=None,
    execute_result="UPDATE 1",
):
    if fetchrow_results is not None and not isinstance(fetchrow_results, list):
        fetchrow_results = [fetchrow_results]
    if fetch_results is not None and not isinstance(fetch_results, list):
        fetch_results = [fetch_results]

    @asynccontextmanager
    async def _fake():
        conn = AsyncMock()
        _fetchrow_idx = [0]
        _fetch_idx = [0]

        async def _fetchrow(*args, **kwargs):
            if fetchrow_results is None:
                return None
            idx = _fetchrow_idx[0]
            _fetchrow_idx[0] += 1
            if idx < len(fetchrow_results):
                return fetchrow_results[idx]
            return fetchrow_results[-1] if fetchrow_results else None

        async def _fetch(*args, **kwargs):
            if fetch_results is None:
                return []
            idx = _fetch_idx[0]
            _fetch_idx[0] += 1
            if idx < len(fetch_results):
                return fetch_results[idx]
            return fetch_results[-1] if fetch_results else []

        conn.fetchrow = _fetchrow
        conn.fetch = _fetch
        conn.execute = AsyncMock(return_value=execute_result)
        yield conn

    return _fake


@pytest.fixture
def client() -> TestClient:
    return TestClient(app, raise_server_exceptions=False)


# ---------------------------------------------------------------------------
# List payments
# ---------------------------------------------------------------------------


def test_list_payments_returns_payments(
    client: TestClient, make_test_jwt: Callable[..., str], monkeypatch
) -> None:
    import dailyriff_api.routers.payments as mod

    monkeypatch.setattr(
        mod,
        "service_transaction",
        _make_service_ctx(
            fetchrow_results=[TEACHER_MEMBERSHIP],
            fetch_results=[[PAYMENT_ROW]],
        ),
    )

    token = make_test_jwt(user_id=USER_A_ID)
    resp = client.get(
        f"/studios/{STUDIO_ID}/payments",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["amount"] == "50.00"
    assert data[0]["memo"] == "March lesson fee"


# ---------------------------------------------------------------------------
# Add payment
# ---------------------------------------------------------------------------


def test_add_payment(
    client: TestClient, make_test_jwt: Callable[..., str], monkeypatch
) -> None:
    import dailyriff_api.routers.payments as mod

    monkeypatch.setattr(
        mod,
        "service_transaction",
        _make_service_ctx(
            fetchrow_results=[TEACHER_MEMBERSHIP, PAYMENT_ROW],
        ),
    )

    token = make_test_jwt(user_id=USER_A_ID)
    resp = client.post(
        f"/studios/{STUDIO_ID}/payments",
        json={
            "student_user_id": str(STUDENT_USER_ID),
            "amount": "50.00",
            "method": "cash",
            "memo": "March lesson fee",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    assert resp.json()["amount"] == "50.00"
    assert resp.json()["memo"] == "March lesson fee"


# ---------------------------------------------------------------------------
# Get payment
# ---------------------------------------------------------------------------


def test_get_payment(
    client: TestClient, make_test_jwt: Callable[..., str], monkeypatch
) -> None:
    import dailyriff_api.routers.payments as mod

    monkeypatch.setattr(
        mod,
        "service_transaction",
        _make_service_ctx(
            fetchrow_results=[TEACHER_MEMBERSHIP, PAYMENT_ROW],
        ),
    )

    token = make_test_jwt(user_id=USER_A_ID)
    resp = client.get(
        f"/studios/{STUDIO_ID}/payments/{PAYMENT_ID}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["amount"] == "50.00"


def test_get_payment_not_found(
    client: TestClient, make_test_jwt: Callable[..., str], monkeypatch
) -> None:
    import dailyriff_api.routers.payments as mod

    monkeypatch.setattr(
        mod,
        "service_transaction",
        _make_service_ctx(
            fetchrow_results=[TEACHER_MEMBERSHIP, None],
        ),
    )

    token = make_test_jwt(user_id=USER_A_ID)
    resp = client.get(
        f"/studios/{STUDIO_ID}/payments/{uuid.uuid4()}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Refund payment
# ---------------------------------------------------------------------------


def test_refund_payment(
    client: TestClient, make_test_jwt: Callable[..., str], monkeypatch
) -> None:
    import dailyriff_api.routers.payments as mod

    refunded_row = {**PAYMENT_ROW, "status": "refunded", "refunded_at": NOW}
    monkeypatch.setattr(
        mod,
        "service_transaction",
        _make_service_ctx(
            fetchrow_results=[TEACHER_MEMBERSHIP, refunded_row],
        ),
    )

    token = make_test_jwt(user_id=USER_A_ID)
    resp = client.post(
        f"/studios/{STUDIO_ID}/payments/{PAYMENT_ID}/refund",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "refunded"
    assert data["refunded_at"] is not None


def test_refund_payment_not_found(
    client: TestClient, make_test_jwt: Callable[..., str], monkeypatch
) -> None:
    import dailyriff_api.routers.payments as mod

    monkeypatch.setattr(
        mod,
        "service_transaction",
        _make_service_ctx(
            fetchrow_results=[TEACHER_MEMBERSHIP, None],
        ),
    )

    token = make_test_jwt(user_id=USER_A_ID)
    resp = client.post(
        f"/studios/{STUDIO_ID}/payments/{uuid.uuid4()}/refund",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Outstanding balance
# ---------------------------------------------------------------------------


def test_outstanding_balance(
    client: TestClient, make_test_jwt: Callable[..., str], monkeypatch
) -> None:
    import dailyriff_api.routers.payments as mod

    balance_row = {
        "total_pending": Decimal("100.00"),
        "total_paid": Decimal("50.00"),
        "total_refunded": Decimal("25.00"),
    }
    monkeypatch.setattr(
        mod,
        "service_transaction",
        _make_service_ctx(
            fetchrow_results=[TEACHER_MEMBERSHIP, balance_row],
        ),
    )

    token = make_test_jwt(user_id=USER_A_ID)
    resp = client.get(
        f"/studios/{STUDIO_ID}/payments/outstanding/{STUDENT_USER_ID}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_pending"] == "100.00"
    assert data["total_paid"] == "50.00"
    assert data["total_refunded"] == "25.00"
    assert data["student_user_id"] == str(STUDENT_USER_ID)
    assert data["studio_id"] == str(STUDIO_ID)


# ---------------------------------------------------------------------------
# List payments filtered by student
# ---------------------------------------------------------------------------


def test_list_payments_filtered_by_student(
    client: TestClient, make_test_jwt: Callable[..., str], monkeypatch
) -> None:
    import dailyriff_api.routers.payments as mod

    monkeypatch.setattr(
        mod,
        "service_transaction",
        _make_service_ctx(
            fetchrow_results=[TEACHER_MEMBERSHIP],
            fetch_results=[[PAYMENT_ROW]],
        ),
    )

    token = make_test_jwt(user_id=USER_A_ID)
    resp = client.get(
        f"/studios/{STUDIO_ID}/payments?student_user_id={STUDENT_USER_ID}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert len(resp.json()) == 1


# ---------------------------------------------------------------------------
# Update payment
# ---------------------------------------------------------------------------


def test_update_payment(
    client: TestClient, make_test_jwt: Callable[..., str], monkeypatch
) -> None:
    import dailyriff_api.routers.payments as mod

    updated_row = {**PAYMENT_ROW, "status": "paid", "memo": "Paid in full"}
    monkeypatch.setattr(
        mod,
        "service_transaction",
        _make_service_ctx(
            fetchrow_results=[TEACHER_MEMBERSHIP, updated_row],
        ),
    )

    token = make_test_jwt(user_id=USER_A_ID)
    resp = client.patch(
        f"/studios/{STUDIO_ID}/payments/{PAYMENT_ID}",
        json={"status": "paid", "memo": "Paid in full"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "paid"
    assert data["memo"] == "Paid in full"


def test_update_payment_not_found(
    client: TestClient, make_test_jwt: Callable[..., str], monkeypatch
) -> None:
    import dailyriff_api.routers.payments as mod

    monkeypatch.setattr(
        mod,
        "service_transaction",
        _make_service_ctx(
            fetchrow_results=[TEACHER_MEMBERSHIP, None],
        ),
    )

    token = make_test_jwt(user_id=USER_A_ID)
    resp = client.patch(
        f"/studios/{STUDIO_ID}/payments/{uuid.uuid4()}",
        json={"status": "paid"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Access control
# ---------------------------------------------------------------------------


def test_payments_forbidden_for_student(
    client: TestClient, make_test_jwt: Callable[..., str], monkeypatch
) -> None:
    import dailyriff_api.routers.payments as mod

    monkeypatch.setattr(
        mod,
        "service_transaction",
        _make_service_ctx(fetchrow_results=[STUDENT_MEMBERSHIP]),
    )

    token = make_test_jwt(user_id=USER_B_ID)
    resp = client.get(
        f"/studios/{STUDIO_ID}/payments",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403


def test_payments_forbidden_for_non_member(
    client: TestClient, make_test_jwt: Callable[..., str], monkeypatch
) -> None:
    import dailyriff_api.routers.payments as mod

    monkeypatch.setattr(
        mod,
        "service_transaction",
        _make_service_ctx(fetchrow_results=[None]),
    )

    token = make_test_jwt(user_id=USER_B_ID)
    resp = client.get(
        f"/studios/{STUDIO_ID}/payments",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403


def test_unauthenticated_request_rejected(client: TestClient) -> None:
    resp = client.get(f"/studios/{STUDIO_ID}/payments")
    assert resp.status_code == 401


def test_list_payments_empty(
    client: TestClient, make_test_jwt: Callable[..., str], monkeypatch
) -> None:
    import dailyriff_api.routers.payments as mod

    monkeypatch.setattr(
        mod,
        "service_transaction",
        _make_service_ctx(
            fetchrow_results=[TEACHER_MEMBERSHIP],
            fetch_results=[[]],
        ),
    )

    token = make_test_jwt(user_id=USER_A_ID)
    resp = client.get(
        f"/studios/{STUDIO_ID}/payments",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json() == []

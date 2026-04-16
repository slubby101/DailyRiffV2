"""Account conversion router unit tests with mocked DB."""

from __future__ import annotations

import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Callable
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from dailyriff_api.main import app
from tests.conftest import USER_A_ID, USER_B_ID

NOW = datetime.now(timezone.utc)
STUDIO_ID = uuid.uuid4()
CHILD_USER_ID = uuid.uuid4()
MEMBER_ROW_ID = uuid.uuid4()

TEACHER_MEMBERSHIP = {"role": "teacher"}
STUDENT_MEMBERSHIP = {"role": "student"}
PARENT_MEMBERSHIP = {"role": "parent"}

MINOR_STUDENT = {"age_class": "minor"}
TEEN_STUDENT = {"age_class": "teen"}
ADULT_STUDENT = {"age_class": "adult"}
NO_AGE_STUDENT = {"age_class": None}

UPDATED_MEMBER_ROW = {
    "id": MEMBER_ROW_ID,
    "studio_id": STUDIO_ID,
    "user_id": CHILD_USER_ID,
    "role": "student",
    "age_class": "teen",
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

    @asynccontextmanager
    async def _fake():
        conn = AsyncMock()
        _fetchrow_idx = [0]

        async def _fetchrow(*args, **kwargs):
            if fetchrow_results is None:
                return None
            idx = _fetchrow_idx[0]
            _fetchrow_idx[0] += 1
            if idx < len(fetchrow_results):
                return fetchrow_results[idx]
            return fetchrow_results[-1] if fetchrow_results else None

        conn.fetchrow = _fetchrow
        conn.execute = AsyncMock(return_value=execute_result)
        yield conn

    return _fake


@pytest.fixture
def client() -> TestClient:
    return TestClient(app, raise_server_exceptions=False)


# ---------------------------------------------------------------------------
# Eligibility endpoint
# ---------------------------------------------------------------------------


def test_eligibility_returns_conversions_for_minor(
    client: TestClient, make_test_jwt: Callable[..., str], monkeypatch
) -> None:
    import dailyriff_api.routers.account_conversion as mod

    monkeypatch.setattr(
        mod,
        "service_transaction",
        _make_service_ctx(
            fetchrow_results=[TEACHER_MEMBERSHIP, MINOR_STUDENT],
        ),
    )

    token = make_test_jwt(user_id=USER_A_ID)
    resp = client.get(
        f"/studios/{STUDIO_ID}/students/{CHILD_USER_ID}/conversion-eligibility",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["current"] == "minor"
    targets = [c["target"] for c in data["conversions"]]
    assert "teen" in targets
    assert "adult" in targets


def test_eligibility_returns_empty_for_adult(
    client: TestClient, make_test_jwt: Callable[..., str], monkeypatch
) -> None:
    import dailyriff_api.routers.account_conversion as mod

    monkeypatch.setattr(
        mod,
        "service_transaction",
        _make_service_ctx(
            fetchrow_results=[TEACHER_MEMBERSHIP, ADULT_STUDENT],
        ),
    )

    token = make_test_jwt(user_id=USER_A_ID)
    resp = client.get(
        f"/studios/{STUDIO_ID}/students/{CHILD_USER_ID}/conversion-eligibility",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["conversions"] == []


def test_eligibility_404_for_missing_student(
    client: TestClient, make_test_jwt: Callable[..., str], monkeypatch
) -> None:
    import dailyriff_api.routers.account_conversion as mod

    monkeypatch.setattr(
        mod,
        "service_transaction",
        _make_service_ctx(
            fetchrow_results=[TEACHER_MEMBERSHIP, None],
        ),
    )

    token = make_test_jwt(user_id=USER_A_ID)
    resp = client.get(
        f"/studios/{STUDIO_ID}/students/{CHILD_USER_ID}/conversion-eligibility",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404


def test_eligibility_403_for_student_role(
    client: TestClient, make_test_jwt: Callable[..., str], monkeypatch
) -> None:
    import dailyriff_api.routers.account_conversion as mod

    monkeypatch.setattr(
        mod,
        "service_transaction",
        _make_service_ctx(
            fetchrow_results=[STUDENT_MEMBERSHIP],
        ),
    )

    token = make_test_jwt(user_id=USER_B_ID)
    resp = client.get(
        f"/studios/{STUDIO_ID}/students/{CHILD_USER_ID}/conversion-eligibility",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403


def test_eligibility_401_without_auth(client: TestClient) -> None:
    resp = client.get(
        f"/studios/{STUDIO_ID}/students/{CHILD_USER_ID}/conversion-eligibility",
    )
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Convert endpoint
# ---------------------------------------------------------------------------


def test_convert_minor_to_teen_with_consent(
    client: TestClient, make_test_jwt: Callable[..., str], monkeypatch
) -> None:
    import dailyriff_api.routers.account_conversion as mod
    import dailyriff_api.services.account_conversion_service as svc_mod

    # Router reads student age_class, then service does the convert
    monkeypatch.setattr(
        mod,
        "service_transaction",
        _make_service_ctx(
            fetchrow_results=[TEACHER_MEMBERSHIP, MINOR_STUDENT],
        ),
    )
    monkeypatch.setattr(
        svc_mod,
        "service_transaction",
        _make_service_ctx(
            fetchrow_results=[UPDATED_MEMBER_ROW],
        ),
    )

    token = make_test_jwt(user_id=USER_A_ID)
    resp = client.post(
        f"/studios/{STUDIO_ID}/students/{CHILD_USER_ID}/convert",
        json={
            "target_age_class": "teen",
            "parent_consent_given": True,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["previous_age_class"] == "minor"
    assert data["new_age_class"] == "teen"
    assert data["parent_access_removed"] is False


def test_convert_teen_to_adult_with_email(
    client: TestClient, make_test_jwt: Callable[..., str], monkeypatch
) -> None:
    import dailyriff_api.routers.account_conversion as mod
    import dailyriff_api.services.account_conversion_service as svc_mod

    adult_row = {**UPDATED_MEMBER_ROW, "age_class": "adult"}

    monkeypatch.setattr(
        mod,
        "service_transaction",
        _make_service_ctx(
            fetchrow_results=[TEACHER_MEMBERSHIP, TEEN_STUDENT],
        ),
    )
    monkeypatch.setattr(
        svc_mod,
        "service_transaction",
        _make_service_ctx(
            fetchrow_results=[adult_row],
        ),
    )

    token = make_test_jwt(user_id=USER_A_ID)
    resp = client.post(
        f"/studios/{STUDIO_ID}/students/{CHILD_USER_ID}/convert",
        json={
            "target_age_class": "adult",
            "new_email": "student@example.com",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["new_age_class"] == "adult"
    assert data["parent_access_removed"] is True


def test_convert_without_consent_returns_422(
    client: TestClient, make_test_jwt: Callable[..., str], monkeypatch
) -> None:
    import dailyriff_api.routers.account_conversion as mod

    monkeypatch.setattr(
        mod,
        "service_transaction",
        _make_service_ctx(
            fetchrow_results=[TEACHER_MEMBERSHIP, MINOR_STUDENT],
        ),
    )

    token = make_test_jwt(user_id=USER_A_ID)
    resp = client.post(
        f"/studios/{STUDIO_ID}/students/{CHILD_USER_ID}/convert",
        json={
            "target_age_class": "teen",
            "parent_consent_given": False,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 422
    assert "consent" in resp.json()["detail"].lower()


def test_convert_403_for_parent_role(
    client: TestClient, make_test_jwt: Callable[..., str], monkeypatch
) -> None:
    import dailyriff_api.routers.account_conversion as mod

    monkeypatch.setattr(
        mod,
        "service_transaction",
        _make_service_ctx(
            fetchrow_results=[PARENT_MEMBERSHIP],
        ),
    )

    token = make_test_jwt(user_id=USER_B_ID)
    resp = client.post(
        f"/studios/{STUDIO_ID}/students/{CHILD_USER_ID}/convert",
        json={
            "target_age_class": "teen",
            "parent_consent_given": True,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403

"""Teacher-students router unit tests with mocked DB."""

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
STUDENT_USER_ID = uuid.uuid4()
PARENT_USER_ID = uuid.uuid4()
PARENT_ID = uuid.uuid4()
PC_ID = uuid.uuid4()
LOAN_ID = uuid.uuid4()

TEACHER_MEMBERSHIP = {"role": "teacher"}
STUDENT_MEMBERSHIP = {"role": "student"}

STUDENT_ROW = {
    "user_id": STUDENT_USER_ID,
    "email": "student@test.local",
    "role": "student",
    "joined_at": NOW,
}

PARENT_CHILD_ROW = {
    "id": PC_ID,
    "parent_id": PARENT_ID,
    "parent_user_id": PARENT_USER_ID,
    "child_user_id": STUDENT_USER_ID,
    "is_primary_contact": True,
    "can_manage_payments": True,
    "can_view_progress": True,
    "can_communicate_with_teacher": True,
    "created_at": NOW,
}

LOAN_ROW = {
    "id": LOAN_ID,
    "studio_id": STUDIO_ID,
    "student_user_id": STUDENT_USER_ID,
    "item_name": "Violin #3",
    "description": "3/4 size student violin",
    "loaned_at": NOW,
    "returned_at": None,
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
    """Create a service_transaction mock.

    fetchrow_results can be a list — each call pops from front (first call
    returns first element, etc.). If a single value is given it's returned
    for every call.
    """
    if fetchrow_results is not None and not isinstance(fetchrow_results, list):
        fetchrow_results = [fetchrow_results]
    if fetch_results is not None and not isinstance(fetch_results, list):
        fetch_results = [fetch_results]

    @asynccontextmanager
    async def _fake():
        conn = AsyncMock()
        # Track call index for sequential fetchrow results
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
# Student list
# ---------------------------------------------------------------------------


def test_list_students_returns_students(
    client: TestClient, make_test_jwt: Callable[..., str], monkeypatch
) -> None:
    import dailyriff_api.routers.teacher_students as mod

    monkeypatch.setattr(
        mod,
        "service_transaction",
        _make_service_ctx(
            fetchrow_results=[TEACHER_MEMBERSHIP],
            fetch_results=[[STUDENT_ROW]],
        ),
    )

    token = make_test_jwt(user_id=USER_A_ID)
    resp = client.get(
        f"/studios/{STUDIO_ID}/students",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["email"] == "student@test.local"


def test_list_students_empty(
    client: TestClient, make_test_jwt: Callable[..., str], monkeypatch
) -> None:
    import dailyriff_api.routers.teacher_students as mod

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
        f"/studios/{STUDIO_ID}/students",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json() == []


def test_list_students_forbidden_for_non_teacher(
    client: TestClient, make_test_jwt: Callable[..., str], monkeypatch
) -> None:
    import dailyriff_api.routers.teacher_students as mod

    monkeypatch.setattr(
        mod,
        "service_transaction",
        _make_service_ctx(fetchrow_results=[STUDENT_MEMBERSHIP]),
    )

    token = make_test_jwt(user_id=USER_B_ID)
    resp = client.get(
        f"/studios/{STUDIO_ID}/students",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403


def test_list_students_forbidden_for_non_member(
    client: TestClient, make_test_jwt: Callable[..., str], monkeypatch
) -> None:
    import dailyriff_api.routers.teacher_students as mod

    monkeypatch.setattr(
        mod,
        "service_transaction",
        _make_service_ctx(fetchrow_results=[None]),
    )

    token = make_test_jwt(user_id=USER_B_ID)
    resp = client.get(
        f"/studios/{STUDIO_ID}/students",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403


def test_list_students_with_search(
    client: TestClient, make_test_jwt: Callable[..., str], monkeypatch
) -> None:
    import dailyriff_api.routers.teacher_students as mod

    monkeypatch.setattr(
        mod,
        "service_transaction",
        _make_service_ctx(
            fetchrow_results=[TEACHER_MEMBERSHIP],
            fetch_results=[[STUDENT_ROW]],
        ),
    )

    token = make_test_jwt(user_id=USER_A_ID)
    resp = client.get(
        f"/studios/{STUDIO_ID}/students?search=student",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert len(resp.json()) == 1


# ---------------------------------------------------------------------------
# Student detail
# ---------------------------------------------------------------------------


def test_get_student_detail(
    client: TestClient, make_test_jwt: Callable[..., str], monkeypatch
) -> None:
    import dailyriff_api.routers.teacher_students as mod

    monkeypatch.setattr(
        mod,
        "service_transaction",
        _make_service_ctx(
            fetchrow_results=[TEACHER_MEMBERSHIP, STUDENT_ROW],
            fetch_results=[[PARENT_CHILD_ROW], [LOAN_ROW]],
        ),
    )

    token = make_test_jwt(user_id=USER_A_ID)
    resp = client.get(
        f"/studios/{STUDIO_ID}/students/{STUDENT_USER_ID}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["email"] == "student@test.local"
    assert len(data["parents"]) == 1
    assert data["parents"][0]["children"][0]["is_primary_contact"] is True
    assert len(data["loans"]) == 1
    assert data["loans"][0]["item_name"] == "Violin #3"


def test_get_student_detail_not_found(
    client: TestClient, make_test_jwt: Callable[..., str], monkeypatch
) -> None:
    import dailyriff_api.routers.teacher_students as mod

    monkeypatch.setattr(
        mod,
        "service_transaction",
        _make_service_ctx(
            fetchrow_results=[TEACHER_MEMBERSHIP, None],
        ),
    )

    token = make_test_jwt(user_id=USER_A_ID)
    resp = client.get(
        f"/studios/{STUDIO_ID}/students/{uuid.uuid4()}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Parent-child permission update
# ---------------------------------------------------------------------------


def test_update_parent_child_permissions(
    client: TestClient, make_test_jwt: Callable[..., str], monkeypatch
) -> None:
    import dailyriff_api.routers.teacher_students as mod

    updated_row = {
        "id": PC_ID,
        "parent_id": PARENT_ID,
        "child_user_id": STUDENT_USER_ID,
        "is_primary_contact": True,
        "can_manage_payments": False,
        "can_view_progress": True,
        "can_communicate_with_teacher": True,
        "created_at": NOW,
    }
    parent_row = {"user_id": PARENT_USER_ID}

    # First service_transaction: membership check + existing check + update
    # Second service_transaction: fetch parent user_id
    call_count = [0]

    @asynccontextmanager
    async def _fake():
        nonlocal call_count
        call_count[0] += 1
        conn = AsyncMock()
        if call_count[0] == 1:
            _idx = [0]
            results = [TEACHER_MEMBERSHIP, {"id": PC_ID}, updated_row]

            async def _fr(*a, **kw):
                i = _idx[0]
                _idx[0] += 1
                return results[i] if i < len(results) else None

            conn.fetchrow = _fr
        else:
            conn.fetchrow = AsyncMock(return_value=parent_row)
        yield conn

    monkeypatch.setattr(mod, "service_transaction", _fake)

    token = make_test_jwt(user_id=USER_A_ID)
    resp = client.patch(
        f"/studios/{STUDIO_ID}/parent-children/{PC_ID}",
        json={"can_manage_payments": False},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["can_manage_payments"] is False


def test_update_parent_child_permissions_not_found(
    client: TestClient, make_test_jwt: Callable[..., str], monkeypatch
) -> None:
    import dailyriff_api.routers.teacher_students as mod

    monkeypatch.setattr(
        mod,
        "service_transaction",
        _make_service_ctx(
            fetchrow_results=[TEACHER_MEMBERSHIP, None],
        ),
    )

    token = make_test_jwt(user_id=USER_A_ID)
    resp = client.patch(
        f"/studios/{STUDIO_ID}/parent-children/{uuid.uuid4()}",
        json={"can_manage_payments": False},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404


def test_update_parent_child_permissions_no_fields(
    client: TestClient, make_test_jwt: Callable[..., str], monkeypatch
) -> None:
    import dailyriff_api.routers.teacher_students as mod

    monkeypatch.setattr(
        mod,
        "service_transaction",
        _make_service_ctx(fetchrow_results=[TEACHER_MEMBERSHIP]),
    )

    token = make_test_jwt(user_id=USER_A_ID)
    resp = client.patch(
        f"/studios/{STUDIO_ID}/parent-children/{PC_ID}",
        json={},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Loans CRUD
# ---------------------------------------------------------------------------


def test_list_loans(
    client: TestClient, make_test_jwt: Callable[..., str], monkeypatch
) -> None:
    import dailyriff_api.routers.teacher_students as mod

    monkeypatch.setattr(
        mod,
        "service_transaction",
        _make_service_ctx(
            fetchrow_results=[TEACHER_MEMBERSHIP],
            fetch_results=[[LOAN_ROW]],
        ),
    )

    token = make_test_jwt(user_id=USER_A_ID)
    resp = client.get(
        f"/studios/{STUDIO_ID}/loans",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["item_name"] == "Violin #3"


def test_list_loans_filtered_by_student(
    client: TestClient, make_test_jwt: Callable[..., str], monkeypatch
) -> None:
    import dailyriff_api.routers.teacher_students as mod

    monkeypatch.setattr(
        mod,
        "service_transaction",
        _make_service_ctx(
            fetchrow_results=[TEACHER_MEMBERSHIP],
            fetch_results=[[LOAN_ROW]],
        ),
    )

    token = make_test_jwt(user_id=USER_A_ID)
    resp = client.get(
        f"/studios/{STUDIO_ID}/loans?student_user_id={STUDENT_USER_ID}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert len(resp.json()) == 1


def test_create_loan(
    client: TestClient, make_test_jwt: Callable[..., str], monkeypatch
) -> None:
    import dailyriff_api.routers.teacher_students as mod

    monkeypatch.setattr(
        mod,
        "service_transaction",
        _make_service_ctx(
            fetchrow_results=[TEACHER_MEMBERSHIP, LOAN_ROW],
        ),
    )

    token = make_test_jwt(user_id=USER_A_ID)
    resp = client.post(
        f"/studios/{STUDIO_ID}/loans",
        json={
            "studio_id": str(STUDIO_ID),
            "student_user_id": str(STUDENT_USER_ID),
            "item_name": "Violin #3",
            "description": "3/4 size student violin",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    assert resp.json()["item_name"] == "Violin #3"


def test_get_loan(
    client: TestClient, make_test_jwt: Callable[..., str], monkeypatch
) -> None:
    import dailyriff_api.routers.teacher_students as mod

    monkeypatch.setattr(
        mod,
        "service_transaction",
        _make_service_ctx(
            fetchrow_results=[TEACHER_MEMBERSHIP, LOAN_ROW],
        ),
    )

    token = make_test_jwt(user_id=USER_A_ID)
    resp = client.get(
        f"/studios/{STUDIO_ID}/loans/{LOAN_ID}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["item_name"] == "Violin #3"


def test_get_loan_not_found(
    client: TestClient, make_test_jwt: Callable[..., str], monkeypatch
) -> None:
    import dailyriff_api.routers.teacher_students as mod

    monkeypatch.setattr(
        mod,
        "service_transaction",
        _make_service_ctx(
            fetchrow_results=[TEACHER_MEMBERSHIP, None],
        ),
    )

    token = make_test_jwt(user_id=USER_A_ID)
    resp = client.get(
        f"/studios/{STUDIO_ID}/loans/{uuid.uuid4()}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404


def test_update_loan_mark_returned(
    client: TestClient, make_test_jwt: Callable[..., str], monkeypatch
) -> None:
    import dailyriff_api.routers.teacher_students as mod

    returned_row = {**LOAN_ROW, "returned_at": NOW}
    monkeypatch.setattr(
        mod,
        "service_transaction",
        _make_service_ctx(
            fetchrow_results=[TEACHER_MEMBERSHIP, returned_row],
        ),
    )

    token = make_test_jwt(user_id=USER_A_ID)
    resp = client.patch(
        f"/studios/{STUDIO_ID}/loans/{LOAN_ID}",
        json={"returned_at": NOW.isoformat()},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["returned_at"] is not None


def test_update_loan_not_found(
    client: TestClient, make_test_jwt: Callable[..., str], monkeypatch
) -> None:
    import dailyriff_api.routers.teacher_students as mod

    monkeypatch.setattr(
        mod,
        "service_transaction",
        _make_service_ctx(
            fetchrow_results=[TEACHER_MEMBERSHIP, None],
        ),
    )

    token = make_test_jwt(user_id=USER_A_ID)
    resp = client.patch(
        f"/studios/{STUDIO_ID}/loans/{uuid.uuid4()}",
        json={"item_name": "Nope"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404


def test_delete_loan(
    client: TestClient, make_test_jwt: Callable[..., str], monkeypatch
) -> None:
    import dailyriff_api.routers.teacher_students as mod

    monkeypatch.setattr(
        mod,
        "service_transaction",
        _make_service_ctx(
            fetchrow_results=[TEACHER_MEMBERSHIP],
            execute_result="DELETE 1",
        ),
    )

    token = make_test_jwt(user_id=USER_A_ID)
    resp = client.delete(
        f"/studios/{STUDIO_ID}/loans/{LOAN_ID}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 204


def test_delete_loan_not_found(
    client: TestClient, make_test_jwt: Callable[..., str], monkeypatch
) -> None:
    import dailyriff_api.routers.teacher_students as mod

    monkeypatch.setattr(
        mod,
        "service_transaction",
        _make_service_ctx(
            fetchrow_results=[TEACHER_MEMBERSHIP],
            execute_result="DELETE 0",
        ),
    )

    token = make_test_jwt(user_id=USER_A_ID)
    resp = client.delete(
        f"/studios/{STUDIO_ID}/loans/{uuid.uuid4()}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404


def test_unauthenticated_request_rejected(client: TestClient) -> None:
    resp = client.get(f"/studios/{STUDIO_ID}/students")
    assert resp.status_code == 401


def test_loans_forbidden_for_student(
    client: TestClient, make_test_jwt: Callable[..., str], monkeypatch
) -> None:
    import dailyriff_api.routers.teacher_students as mod

    monkeypatch.setattr(
        mod,
        "service_transaction",
        _make_service_ctx(fetchrow_results=[STUDENT_MEMBERSHIP]),
    )

    token = make_test_jwt(user_id=USER_B_ID)
    resp = client.get(
        f"/studios/{STUDIO_ID}/loans",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403

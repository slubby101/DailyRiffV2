"""Device / push-subscription endpoint stubs.

Stage 0 slice c ships these as authenticated stubs — they return 401 without
a valid token and an empty-shaped response with a valid token. Slice d wires
them to the database.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, status

from dailyriff_api.auth import CurrentUser, get_current_user

router = APIRouter(prefix="/devices", tags=["devices"])


@router.get("")
def list_devices(user: CurrentUser = Depends(get_current_user)) -> list[dict]:
    return []


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register_device(
    payload: dict, user: CurrentUser = Depends(get_current_user)
) -> dict:
    return {"id": None, "user_id": str(user.id), **payload}


@router.delete("/{device_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_device(
    device_id: UUID, user: CurrentUser = Depends(get_current_user)
) -> None:
    return None

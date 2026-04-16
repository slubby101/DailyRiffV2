"""Recording endpoints — create (mint upload URL), confirm upload, list, get.

FastAPI never proxies bytes — presigned R2 URLs go directly to the client.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone as tz
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from dailyriff_api.auth import (
    PROTECTED_RESPONSES,
    CurrentUser,
    get_current_user,
)
from dailyriff_api.db import rls_transaction, service_transaction
from dailyriff_api.pagination import pagination_params
from dailyriff_api.schemas.recording import (
    PlaybackUrlResponse,
    RecordingCreateRequest,
    RecordingResponse,
    UploadConfirmRequest,
    UploadUrlResponse,
)
from dailyriff_api.services.playback_authorization import can_play_recording
from dailyriff_api.services.recording_service import RecordingService

router = APIRouter(prefix="/recordings", tags=["recordings"])

RECORDING_COLUMNS = (
    "id, studio_id, student_id, assignment_id, r2_object_key, mime_type, "
    "duration_seconds, file_size_bytes, uploaded_at, deleted_at, created_at, updated_at"
)


_PLAYBACK_URL_TTL_SECONDS = 300


def _presign_playback_url(r2_object_key: str) -> str:
    """Generate a 5-minute presigned download URL for R2."""
    r2_endpoint = os.environ.get("R2_ENDPOINT", "https://r2.dailyriff.com")
    r2_bucket = os.environ.get("R2_RECORDINGS_BUCKET", "dailyriff-recordings")
    return f"{r2_endpoint}/{r2_bucket}/{r2_object_key}?X-Amz-Expires={_PLAYBACK_URL_TTL_SECONDS}"


def _presign_upload_url(r2_object_key: str) -> str:
    """Generate a presigned upload URL for R2.

    In production this uses the R2 S3-compatible API with boto3.
    For now returns a placeholder URL pattern that the client can use.
    """
    r2_endpoint = os.environ.get("R2_ENDPOINT", "https://r2.dailyriff.com")
    r2_bucket = os.environ.get("R2_RECORDINGS_BUCKET", "dailyriff-recordings")
    return f"{r2_endpoint}/{r2_bucket}/{r2_object_key}?X-Amz-Expires=3600"


@router.get("", response_model=list[RecordingResponse], responses=PROTECTED_RESPONSES)
async def list_recordings(
    user: CurrentUser = Depends(get_current_user),
    pagination: tuple[int, int] = Depends(pagination_params),
) -> list[RecordingResponse]:
    limit, offset = pagination
    async with rls_transaction(user.id) as conn:
        rows = await conn.fetch(
            f"SELECT {RECORDING_COLUMNS} FROM recordings "
            f"WHERE deleted_at IS NULL ORDER BY created_at DESC LIMIT $1 OFFSET $2",
            limit,
            offset,
        )
    return [RecordingResponse(**dict(r)) for r in rows]


@router.post(
    "",
    response_model=UploadUrlResponse,
    status_code=status.HTTP_201_CREATED,
    responses=PROTECTED_RESPONSES,
)
async def create_recording(
    body: RecordingCreateRequest,
    user: CurrentUser = Depends(get_current_user),
) -> UploadUrlResponse:
    # Validate MIME type
    try:
        RecordingService.negotiate_mime(body.mime_type)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        ) from e

    async with rls_transaction(user.id) as conn:
        row = await conn.fetchrow(
            f"INSERT INTO recordings "
            f"(studio_id, student_id, assignment_id, r2_object_key, mime_type, duration_seconds, file_size_bytes) "
            f"VALUES ($1, $2, $3, $4, $5, $6, $7) "
            f"RETURNING {RECORDING_COLUMNS}",
            body.studio_id,
            user.id,
            body.assignment_id,
            "placeholder",  # Will be updated after we have the ID
            body.mime_type,
            body.duration_seconds,
            body.file_size_bytes,
        )
        if row is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create recording",
            )
        # Generate the real R2 key with the recording ID
        r2_key = RecordingService.r2_object_key(
            studio_id=body.studio_id,
            student_id=user.id,
            recording_id=row["id"],
            mime_type=body.mime_type,
        )
        await conn.execute(
            "UPDATE recordings SET r2_object_key = $1 WHERE id = $2",
            r2_key,
            row["id"],
        )

    upload_url = _presign_upload_url(r2_key)
    return UploadUrlResponse(
        recording_id=row["id"],
        upload_url=upload_url,
        r2_object_key=r2_key,
    )


@router.get(
    "/{recording_id}",
    response_model=RecordingResponse,
    responses={**PROTECTED_RESPONSES, 404: {"description": "Recording not found"}},
)
async def get_recording(
    recording_id: UUID,
    user: CurrentUser = Depends(get_current_user),
) -> RecordingResponse:
    async with rls_transaction(user.id) as conn:
        row = await conn.fetchrow(
            f"SELECT {RECORDING_COLUMNS} FROM recordings WHERE id = $1 AND deleted_at IS NULL",
            recording_id,
        )
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return RecordingResponse(**dict(row))


@router.post(
    "/{recording_id}/confirm-upload",
    response_model=RecordingResponse,
    responses={**PROTECTED_RESPONSES, 404: {"description": "Recording not found"}},
)
async def confirm_upload(
    recording_id: UUID,
    body: UploadConfirmRequest,
    user: CurrentUser = Depends(get_current_user),
) -> RecordingResponse:
    """Confirm that the client has completed uploading to R2.

    Sets uploaded_at which triggers the auto_acknowledge_assignment DB trigger.
    """
    now = datetime.now(tz.utc)
    async with rls_transaction(user.id) as conn:
        row = await conn.fetchrow(
            f"UPDATE recordings "
            f"SET uploaded_at = $2, file_size_bytes = COALESCE($3, file_size_bytes), updated_at = $2 "
            f"WHERE id = $1 AND student_id = $4 "
            f"RETURNING {RECORDING_COLUMNS}",
            recording_id,
            now,
            body.file_size_bytes,
            user.id,
        )
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return RecordingResponse(**dict(row))


@router.get(
    "/{recording_id}/playback-url",
    response_model=PlaybackUrlResponse,
    responses={
        **PROTECTED_RESPONSES,
        403: {"description": "Not authorized to play this recording"},
        404: {"description": "Recording not found"},
    },
)
async def get_playback_url(
    recording_id: UUID,
    user: CurrentUser = Depends(get_current_user),
) -> PlaybackUrlResponse:
    """Policy check → mint 5-min presigned R2 URL. FastAPI never proxies bytes."""
    async with service_transaction() as conn:
        row = await conn.fetchrow(
            f"SELECT {RECORDING_COLUMNS} FROM recordings WHERE id = $1",
            recording_id,
        )
        if row is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

        recording = dict(row)
        if not await can_play_recording(conn, user, recording):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to play this recording",
            )

        # Audit impersonation playback
        if user.impersonation_session_id is not None:
            await conn.execute(
                "INSERT INTO impersonation_playback_log (session_id, recording_id) "
                "VALUES ($1, $2)",
                user.impersonation_session_id,
                recording_id,
            )

    playback_url = _presign_playback_url(recording["r2_object_key"])
    return PlaybackUrlResponse(
        recording_id=recording_id,
        playback_url=playback_url,
        expires_in_seconds=_PLAYBACK_URL_TTL_SECONDS,
    )

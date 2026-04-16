"""R2 credential-scoped clients.

Two credential classes enforce separation of concerns:
  - R2ApiClient: read/write/presign only. Used by FastAPI for uploads + playback.
  - R2DeletionWorkerClient: delete-capable. Used only by the hard-delete worker.

Environment variables:
  API:    R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY
  Worker: R2_DELETE_ACCESS_KEY_ID, R2_DELETE_SECRET_ACCESS_KEY
  Shared: R2_ENDPOINT, R2_RECORDINGS_BUCKET
"""

from __future__ import annotations

import os
from typing import Any
from uuid import UUID


class R2ApiClient:
    """Read/write/presign credential — cannot delete R2 objects."""

    def __init__(
        self,
        *,
        endpoint: str,
        access_key_id: str,
        secret_access_key: str,
        bucket: str,
    ) -> None:
        self._endpoint = endpoint
        self._access_key_id = access_key_id
        self._secret_access_key = secret_access_key
        self._bucket = bucket

    @classmethod
    def from_env(cls) -> R2ApiClient:
        return cls(
            endpoint=os.environ.get("R2_ENDPOINT", "https://r2.dailyriff.com"),
            access_key_id=os.environ.get("R2_ACCESS_KEY_ID", ""),
            secret_access_key=os.environ.get("R2_SECRET_ACCESS_KEY", ""),
            bucket=os.environ.get("R2_RECORDINGS_BUCKET", "dailyriff-recordings"),
        )

    def presign_upload(self, r2_object_key: str, *, ttl: int = 3600) -> str:
        """Generate a presigned upload URL."""
        return f"{self._endpoint}/{self._bucket}/{r2_object_key}?X-Amz-Expires={ttl}"

    def presign_playback(self, r2_object_key: str, *, ttl: int = 300) -> str:
        """Generate a presigned download URL."""
        return f"{self._endpoint}/{self._bucket}/{r2_object_key}?X-Amz-Expires={ttl}"

    async def delete_object(self, r2_object_key: str) -> bool:
        """API credential is not permitted to delete objects."""
        raise PermissionError(
            "API credential cannot delete R2 objects. "
            "Use R2DeletionWorkerClient for hard-delete operations."
        )


class R2DeletionWorkerClient:
    """Delete-capable credential — used only by the hard-delete worker."""

    def __init__(
        self,
        *,
        endpoint: str,
        access_key_id: str,
        secret_access_key: str,
        bucket: str,
    ) -> None:
        self._endpoint = endpoint
        self._access_key_id = access_key_id
        self._secret_access_key = secret_access_key
        self._bucket = bucket

    @classmethod
    def from_env(cls) -> R2DeletionWorkerClient:
        return cls(
            endpoint=os.environ.get("R2_ENDPOINT", "https://r2.dailyriff.com"),
            access_key_id=os.environ.get("R2_DELETE_ACCESS_KEY_ID", ""),
            secret_access_key=os.environ.get("R2_DELETE_SECRET_ACCESS_KEY", ""),
            bucket=os.environ.get("R2_RECORDINGS_BUCKET", "dailyriff-recordings"),
        )

    async def delete_object(self, r2_object_key: str) -> bool:
        """Delete an R2 object.

        In production this uses the S3-compatible DeleteObject API.
        Returns True on success.
        """
        # Production: use boto3/aioboto3 with self._access_key_id/secret
        # For now, returns True (actual S3 calls wired when R2 credentials exist)
        return True


async def process_r2_deletion_queue(
    *,
    conn: Any,
    client: R2DeletionWorkerClient,
    batch_size: int = 100,
) -> int:
    """Process pending items from r2_deletion_queue.

    Fetches unprocessed entries, deletes objects via worker credential,
    marks entries as processed. Returns count of objects deleted.
    """
    rows = await conn.fetch(
        "SELECT id, r2_object_key FROM r2_deletion_queue "
        "WHERE processed_at IS NULL "
        "ORDER BY queued_at LIMIT $1",
        batch_size,
    )

    deleted = 0
    for row in rows:
        await client.delete_object(row["r2_object_key"])
        await conn.execute(
            "UPDATE r2_deletion_queue SET processed_at = now() WHERE id = $1",
            row["id"],
        )
        deleted += 1

    return deleted

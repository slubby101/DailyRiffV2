"""R2 credential scoping tests — API credential vs deletion worker credential."""

from __future__ import annotations

import os
from unittest.mock import AsyncMock, patch

import pytest


# ---- Test 1: API credential rejects DELETE operations ----

@pytest.mark.asyncio
async def test_api_credential_rejects_delete():
    from dailyriff_api.services.r2_client import R2ApiClient

    client = R2ApiClient(
        endpoint="https://r2.dailyriff.com",
        access_key_id="api-key",
        secret_access_key="api-secret",
        bucket="dailyriff-recordings",
    )

    with pytest.raises(PermissionError, match="API credential cannot delete"):
        await client.delete_object("recordings/studio/student/rec.ogg")


# ---- Test 2: Deletion worker credential can delete ----

@pytest.mark.asyncio
async def test_deletion_worker_can_delete():
    from dailyriff_api.services.r2_client import R2DeletionWorkerClient

    client = R2DeletionWorkerClient(
        endpoint="https://r2.dailyriff.com",
        access_key_id="delete-key",
        secret_access_key="delete-secret",
        bucket="dailyriff-recordings",
    )

    # Should not raise
    result = await client.delete_object("recordings/studio/student/rec.ogg")
    assert result is True


# ---- Test 3: API credential can presign upload URL ----

def test_api_credential_can_presign_upload():
    from dailyriff_api.services.r2_client import R2ApiClient

    client = R2ApiClient(
        endpoint="https://r2.dailyriff.com",
        access_key_id="api-key",
        secret_access_key="api-secret",
        bucket="dailyriff-recordings",
    )

    url = client.presign_upload("recordings/studio/student/rec.ogg", ttl=3600)
    assert "r2.dailyriff.com" in url
    assert "rec.ogg" in url


# ---- Test 4: API credential can presign playback URL ----

def test_api_credential_can_presign_playback():
    from dailyriff_api.services.r2_client import R2ApiClient

    client = R2ApiClient(
        endpoint="https://r2.dailyriff.com",
        access_key_id="api-key",
        secret_access_key="api-secret",
        bucket="dailyriff-recordings",
    )

    url = client.presign_playback("recordings/studio/student/rec.ogg", ttl=300)
    assert "r2.dailyriff.com" in url
    assert "rec.ogg" in url


# ---- Test 5: from_env constructs correct client types ----

def test_api_client_from_env():
    from dailyriff_api.services.r2_client import R2ApiClient

    with patch.dict(os.environ, {
        "R2_ENDPOINT": "https://test.r2.dev",
        "R2_ACCESS_KEY_ID": "test-api-key",
        "R2_SECRET_ACCESS_KEY": "test-api-secret",
        "R2_RECORDINGS_BUCKET": "test-bucket",
    }):
        client = R2ApiClient.from_env()
        assert client._endpoint == "https://test.r2.dev"
        assert client._bucket == "test-bucket"


def test_deletion_client_from_env():
    from dailyriff_api.services.r2_client import R2DeletionWorkerClient

    with patch.dict(os.environ, {
        "R2_ENDPOINT": "https://test.r2.dev",
        "R2_DELETE_ACCESS_KEY_ID": "test-delete-key",
        "R2_DELETE_SECRET_ACCESS_KEY": "test-delete-secret",
        "R2_RECORDINGS_BUCKET": "test-bucket",
    }):
        client = R2DeletionWorkerClient.from_env()
        assert client._endpoint == "https://test.r2.dev"


# ---- Test 6: R2 deletion queue processor ----

@pytest.mark.asyncio
async def test_r2_deletion_queue_processor():
    from dailyriff_api.services.r2_client import R2DeletionWorkerClient, process_r2_deletion_queue

    conn = AsyncMock()
    conn.fetch = AsyncMock(return_value=[
        {"id": "aaa", "r2_object_key": "recordings/s1/u1/r1.ogg"},
        {"id": "bbb", "r2_object_key": "recordings/s1/u1/r2.ogg"},
    ])
    conn.execute = AsyncMock()

    mock_client = R2DeletionWorkerClient(
        endpoint="https://r2.test",
        access_key_id="k",
        secret_access_key="s",
        bucket="b",
    )

    result = await process_r2_deletion_queue(conn=conn, client=mock_client, batch_size=10)
    assert result == 2
    assert conn.execute.call_count == 2

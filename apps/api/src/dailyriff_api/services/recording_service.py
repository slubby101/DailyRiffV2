"""Recording service — MIME negotiation, R2 key generation, presigned URL minting.

FastAPI never proxies bytes; presigned URLs go directly to R2.
MIME preference order: opus → mp4a → webm → hard fail.
"""

from __future__ import annotations

from uuid import UUID


# Supported MIME types in preference order
_SUPPORTED_MIMES = {
    "audio/ogg; codecs=opus",
    "audio/webm; codecs=opus",
    "audio/mp4",
    "audio/webm",
}

# MIME → file extension mapping
_MIME_EXTENSIONS: dict[str, str] = {
    "audio/ogg; codecs=opus": "ogg",
    "audio/webm; codecs=opus": "webm",
    "audio/mp4": "m4a",
    "audio/webm": "webm",
}


class RecordingService:
    """Stateless helpers for recording management."""

    @staticmethod
    def negotiate_mime(mime_type: str) -> str:
        """Validate and return the MIME type if supported, else raise ValueError."""
        if mime_type in _SUPPORTED_MIMES:
            return mime_type
        raise ValueError(f"Unsupported MIME type: {mime_type!r}")

    @staticmethod
    def r2_object_key(
        *,
        studio_id: UUID,
        student_id: UUID,
        recording_id: UUID,
        mime_type: str,
    ) -> str:
        """Generate R2 object key: recordings/{studio_id}/{student_id}/{recording_id}.{ext}"""
        ext = _MIME_EXTENSIONS.get(mime_type, "bin")
        return f"recordings/{studio_id}/{student_id}/{recording_id}.{ext}"

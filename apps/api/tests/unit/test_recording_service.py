"""Recording service unit tests — MIME negotiation + R2 key generation."""

from __future__ import annotations

import uuid

import pytest

from dailyriff_api.services.recording_service import RecordingService


STUDIO_ID = uuid.uuid4()
STUDENT_ID = uuid.uuid4()


class TestMimeNegotiation:
    """MIME preference order: opus → mp4a → webm → hard fail."""

    def test_opus_accepted(self):
        mime = RecordingService.negotiate_mime("audio/ogg; codecs=opus")
        assert mime == "audio/ogg; codecs=opus"

    def test_webm_opus_accepted(self):
        mime = RecordingService.negotiate_mime("audio/webm; codecs=opus")
        assert mime == "audio/webm; codecs=opus"

    def test_mp4a_accepted(self):
        mime = RecordingService.negotiate_mime("audio/mp4")
        assert mime == "audio/mp4"

    def test_webm_accepted(self):
        mime = RecordingService.negotiate_mime("audio/webm")
        assert mime == "audio/webm"

    def test_unsupported_mime_rejected(self):
        with pytest.raises(ValueError, match="Unsupported"):
            RecordingService.negotiate_mime("video/mp4")

    def test_empty_mime_rejected(self):
        with pytest.raises(ValueError, match="Unsupported"):
            RecordingService.negotiate_mime("")


class TestR2ObjectKey:
    """R2 object key follows: recordings/{studio_id}/{student_id}/{recording_id}.{ext}"""

    def test_key_format_opus(self):
        rec_id = uuid.uuid4()
        key = RecordingService.r2_object_key(
            studio_id=STUDIO_ID,
            student_id=STUDENT_ID,
            recording_id=rec_id,
            mime_type="audio/ogg; codecs=opus",
        )
        assert key == f"recordings/{STUDIO_ID}/{STUDENT_ID}/{rec_id}.ogg"

    def test_key_format_mp4(self):
        rec_id = uuid.uuid4()
        key = RecordingService.r2_object_key(
            studio_id=STUDIO_ID,
            student_id=STUDENT_ID,
            recording_id=rec_id,
            mime_type="audio/mp4",
        )
        assert key == f"recordings/{STUDIO_ID}/{STUDENT_ID}/{rec_id}.m4a"

    def test_key_format_webm(self):
        rec_id = uuid.uuid4()
        key = RecordingService.r2_object_key(
            studio_id=STUDIO_ID,
            student_id=STUDENT_ID,
            recording_id=rec_id,
            mime_type="audio/webm",
        )
        assert key == f"recordings/{STUDIO_ID}/{STUDENT_ID}/{rec_id}.webm"

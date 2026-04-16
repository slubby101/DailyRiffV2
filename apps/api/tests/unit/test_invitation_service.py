"""Invitation service unit tests — token hashing, age classification, persona routing."""

from __future__ import annotations

from dailyriff_api.services.invitation_service import (
    _hash_token,
    _generate_token,
    classify_age,
    determine_persona_for_age,
)


# --- Token hashing ---


def test_hash_token_produces_consistent_sha256():
    h1 = _hash_token("test-token-123")
    h2 = _hash_token("test-token-123")
    assert h1 == h2
    assert len(h1) == 64  # SHA-256 hex digest


def test_hash_token_different_inputs_produce_different_hashes():
    h1 = _hash_token("token-a")
    h2 = _hash_token("token-b")
    assert h1 != h2


def test_generate_token_returns_plaintext_and_matching_hash():
    plaintext, token_hash = _generate_token()
    assert len(plaintext) > 20  # URL-safe base64, at least 32 bytes
    assert _hash_token(plaintext) == token_hash


# --- Age classification ---


def test_classify_age_under_13_is_minor():
    assert classify_age(5) == "minor"
    assert classify_age(12) == "minor"


def test_classify_age_13_to_17_is_teen():
    assert classify_age(13) == "teen"
    assert classify_age(17) == "teen"


def test_classify_age_18_plus_is_adult():
    assert classify_age(18) == "adult"
    assert classify_age(25) == "adult"


# --- Persona routing by age ---


def test_minor_always_routes_to_parent():
    assert determine_persona_for_age("minor") == "parent"


def test_adult_routes_to_student():
    assert determine_persona_for_age("adult") == "student"


def test_teen_defaults_to_student():
    """Teens default to student; teacher can override to parent."""
    assert determine_persona_for_age("teen") == "student"

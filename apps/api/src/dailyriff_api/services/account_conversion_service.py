"""Account conversion service — manual age-class transitions.

Ports Polymet AccountConversionService domain rules:
  MINOR → TEEN at 13 (requires parent consent)
  MINOR → ADULT at 18 (requires parent consent + new credentials/email)
  TEEN  → ADULT at 18 (requires new credentials/email)

No backward conversions. Birthday-automation deferred to Stage 2.
"""

from __future__ import annotations

from datetime import datetime, timezone as tz
from typing import Any
from uuid import UUID

from dailyriff_api.db import service_transaction

# Valid transitions: (current, target) → requirements
_TRANSITIONS: dict[tuple[str, str], dict[str, bool]] = {
    ("minor", "teen"): {
        "requires_parent_consent": True,
        "requires_new_credentials": False,
    },
    ("minor", "adult"): {
        "requires_parent_consent": True,
        "requires_new_credentials": True,
    },
    ("teen", "adult"): {
        "requires_parent_consent": False,
        "requires_new_credentials": True,
    },
}

_MESSAGES: dict[tuple[str, str], str] = {
    ("minor", "teen"): (
        "Converting this student from a minor to a teen account. "
        "Parent or guardian consent is required before the conversion "
        "can proceed. The parent will retain guardian access."
    ),
    ("minor", "adult"): (
        "Converting this student from a minor to an adult account. "
        "Parent or guardian consent is required, and the student will "
        "need their own email address and login credentials."
    ),
    ("teen", "adult"): (
        "Converting this student from a teen to an adult account. "
        "The student will need their own email address and login "
        "credentials. Parent guardian access will be removed."
    ),
}


class AccountConversionService:
    """Domain rules for manual age-class account conversions."""

    def check_eligibility(self, current_age_class: str) -> dict[str, Any]:
        """Return available conversions for the given age class.

        Each conversion includes target age class, requirements, and message.
        """
        conversions = []
        for (src, tgt), reqs in _TRANSITIONS.items():
            if src == current_age_class:
                conversions.append(
                    {
                        "target": tgt,
                        "requires_parent_consent": reqs["requires_parent_consent"],
                        "requires_new_credentials": reqs["requires_new_credentials"],
                        "message": _MESSAGES[(src, tgt)],
                    }
                )
        return {"current": current_age_class, "conversions": conversions}

    def get_conversion_message(
        self, current_age_class: str, target_age_class: str
    ) -> str:
        """Return the user-facing message for a specific conversion.

        Raises ValueError if the transition is not valid.
        """
        key = (current_age_class, target_age_class)
        if key not in _MESSAGES:
            raise ValueError(
                f"{current_age_class} → {target_age_class} is not a valid conversion"
            )
        return _MESSAGES[key]

    async def convert(
        self,
        *,
        child_user_id: UUID,
        studio_id: UUID,
        current_age_class: str,
        target_age_class: str,
        converted_by: UUID,
        parent_consent_given: bool = False,
        new_email: str | None = None,
    ) -> dict[str, Any]:
        """Perform the account conversion.

        Validates requirements, updates studio_members age_class,
        adjusts parent-child relationships, and logs the activity.
        """
        key = (current_age_class, target_age_class)
        reqs = _TRANSITIONS.get(key)
        if reqs is None:
            raise ValueError(
                f"{current_age_class} → {target_age_class} is not a valid conversion"
            )

        if reqs["requires_parent_consent"] and not parent_consent_given:
            raise ValueError("Parent consent is required for this conversion")

        if reqs["requires_new_credentials"] and not new_email:
            raise ValueError(
                "A new email address is required for this conversion"
            )

        async with service_transaction() as conn:
            # Update the student's age_class in studio_members
            row = await conn.fetchrow(
                """
                UPDATE studio_members
                SET age_class = $1, updated_at = $2
                WHERE studio_id = $3 AND user_id = $4 AND role = 'student'
                RETURNING id, studio_id, user_id, role, age_class, updated_at
                """,
                target_age_class,
                datetime.now(tz.utc),
                studio_id,
                child_user_id,
            )

            if row is None:
                raise ValueError("Student not found in studio")

            # For adult conversion, remove parent guardian access
            if target_age_class == "adult":
                await conn.execute(
                    """
                    DELETE FROM parent_children
                    WHERE child_user_id = $1
                    AND parent_id IN (
                        SELECT id FROM parents WHERE studio_id = $2
                    )
                    """,
                    child_user_id,
                    studio_id,
                )

            # Log the conversion to activity_logs
            await conn.execute(
                """
                INSERT INTO activity_logs (action, entity_type, entity_id,
                    performed_by, details, created_at)
                VALUES ($1, $2, $3, $4, $5, $6)
                """,
                "account_conversion",
                "studio_member",
                row["id"],
                converted_by,
                {
                    "from_age_class": current_age_class,
                    "to_age_class": target_age_class,
                    "child_user_id": str(child_user_id),
                    "studio_id": str(studio_id),
                },
                datetime.now(tz.utc),
            )

            return {
                "child_user_id": child_user_id,
                "studio_id": studio_id,
                "previous_age_class": current_age_class,
                "new_age_class": target_age_class,
                "parent_access_removed": target_age_class == "adult",
                "message": _MESSAGES[key],
            }

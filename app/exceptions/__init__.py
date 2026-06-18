"""Domain exceptions for profile lifecycle operations."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.user_profile import ProfileStatus


class ProfileNotFound(Exception):
    """Raised when a UserProfile cannot be found by ID."""

    def __init__(self, profile_id: int) -> None:
        self.profile_id = profile_id
        super().__init__(f"UserProfile {profile_id} not found")


class IllegalTransitionError(Exception):
    """Raised when a lifecycle transition is not permitted by the state machine."""

    def __init__(
        self,
        profile_id: int,
        current_status: ProfileStatus | str,
        requested_status: ProfileStatus | str,
    ) -> None:
        self.profile_id = profile_id
        self.current_status = getattr(current_status, "value", current_status)
        self.requested_status = getattr(requested_status, "value", requested_status)
        super().__init__(
            f"cannot transition `{self.current_status}` → `{self.requested_status}` "
            f"(profile {profile_id})"
        )


__all__ = ["ProfileNotFound", "IllegalTransitionError"]

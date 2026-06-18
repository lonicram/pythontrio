"""Service for UserProfile lifecycle transitions."""

import logging

from sqlalchemy.orm import Session

from app.exceptions import IllegalTransitionError, ProfileNotFound
from app.models.portfolio import Portfolio
from app.models.user_profile import ProfileStatus, UserProfile

logger = logging.getLogger(__name__)

ALLOWED_TRANSITIONS: dict[ProfileStatus, set[ProfileStatus]] = {
    ProfileStatus.NEW: {ProfileStatus.VERIFIED, ProfileStatus.DELETED},
    ProfileStatus.VERIFIED: {ProfileStatus.SUSPENDED, ProfileStatus.DELETED},
    ProfileStatus.SUSPENDED: {ProfileStatus.VERIFIED, ProfileStatus.DELETED},
    # terminal — no outbound transitions
    ProfileStatus.DELETED: set(),
}


class ProfileLifecycleService:
    """Manages UserProfile lifecycle transitions.

    The service validates the transition, runs side effects, and mutates
    the profile — but does NOT commit. The caller owns the transaction
    boundary (same convention as OnboardingService).
    """

    def __init__(self, db: Session) -> None:
        self.db = db

    def transition(self, profile_id: int, target: ProfileStatus) -> UserProfile:
        """Transition a profile to a new status (caller must commit).

        Args:
            profile_id: ID of the profile to transition.
            target: The desired new status.

        Returns:
            The mutated UserProfile (uncommitted).

        Raises:
            ProfileNotFound: If no profile with profile_id exists.
            IllegalTransitionError: If the transition is not permitted.
        """
        profile = self.db.get(UserProfile, profile_id)
        if profile is None:
            raise ProfileNotFound(profile_id)
        if target not in ALLOWED_TRANSITIONS[profile.status]:
            raise IllegalTransitionError(profile_id, profile.status, target)
        # NOTE: intentionally no version check here
        self._run_side_effects(profile, target)
        profile.status = target
        return profile

    def _run_side_effects(self, profile: UserProfile, target: ProfileStatus) -> None:
        """Run side effects for a lifecycle transition.

        Args:
            profile: The profile being transitioned.
            target: The target status.
        """
        if (
            target == ProfileStatus.VERIFIED
            and profile.status == ProfileStatus.SUSPENDED
        ):
            # Reinstate from suspended — no new portfolio, just re-enable access.
            logger.info("Profile %d reinstated", profile.id)
        elif target == ProfileStatus.VERIFIED:
            # Initial verification (NEW → VERIFIED) — provision starter portfolio.
            portfolio = Portfolio(
                owner_id=profile.id,
                name="Starter Portfolio",
                description="Automatically provisioned on account verification.",
            )
            self.db.add(portfolio)
            logger.info("Provisioned starter portfolio for profile %d", profile.id)
        elif target == ProfileStatus.SUSPENDED:
            logger.info(
                "Profile %d suspended — sessions would be revoked here", profile.id
            )
        elif target == ProfileStatus.DELETED:
            logger.info(
                "Profile %d deleted — portfolios/sessions would be cascade-cleaned here",
                profile.id,
            )

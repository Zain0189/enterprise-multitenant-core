from collections.abc import Sequence
from fastapi import Depends, HTTPException, status

from app.api.deps import SecurityContext, get_current_user_context


class RoleChecker:
    """Enterprise authorization guard enforcing Role-Based Access Control

    (RBAC).

    Can be injected into any FastAPI route dependency chain to restrict access
    to specific authorized roles.
    """

    def __init__(self, allowed_roles: Sequence[str]) -> None:
        # Convert to set for O(1) membership lookup efficiency
        self.allowed_roles = set(allowed_roles)

    def __call__(
        self,
        context: SecurityContext = Depends(get_current_user_context),
    ) -> SecurityContext:
        """Validates that the authenticated user's role is within the allowed

        roles.

        Raises HTTP 403 Forbidden if the role lacks sufficient privilege.
        Returns the verified SecurityContext if authorization succeeds.
        """
        if context.role not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"Forbidden: role '{context.role}' does not have sufficient "
                    f"privileges. Required one of: {list(self.allowed_roles)}"
                ),
            )
        return context


# Standard enterprise permission dependencies ready for route decoration
require_admin = RoleChecker(["admin"])
require_analyst_or_above = RoleChecker(["admin", "analyst"])
require_any_authenticated_user = RoleChecker(["admin", "analyst", "viewer"])

from enum import Enum


class UserRole(str, Enum):
    ADMIN = "admin"
    VIEWER = "viewer"


OPS_ROLES = frozenset({UserRole.ADMIN, UserRole.VIEWER})


def normalize_role(value: str | None) -> UserRole:
    if value == UserRole.VIEWER.value:
        return UserRole.VIEWER
    return UserRole.ADMIN

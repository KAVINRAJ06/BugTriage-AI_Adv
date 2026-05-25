from dataclasses import dataclass

from app.core.roles import UserRole, normalize_role


@dataclass(frozen=True)
class CurrentUser:
    email: str
    role: UserRole

    @property
    def is_admin(self) -> bool:
        return self.role == UserRole.ADMIN

    @property
    def can_write_ops(self) -> bool:
        return self.is_admin


def user_from_doc(doc: dict) -> CurrentUser:
    return CurrentUser(
        email=doc["email"],
        role=normalize_role(doc.get("role")),
    )

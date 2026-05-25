from datetime import datetime, timezone

from app.core.config import settings
from app.core.roles import UserRole
from app.core.security import hash_password
from app.db.mongodb import get_db


async def ensure_default_admin() -> None:
    db = get_db()
    email = settings.admin_email.lower()
    existing = await db.users.find_one({"email": email})
    if existing:
        await db.users.update_one(
            {"email": email},
            {
                "$set": {
                    "role": UserRole.ADMIN.value,
                    "password_hash": hash_password(settings.admin_password),
                }
            },
        )
        return

    await db.users.insert_one(
        {
            "email": email,
            "password_hash": hash_password(settings.admin_password),
            "role": UserRole.ADMIN.value,
            "created_at": datetime.now(timezone.utc),
        }
    )

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.core.config import settings

_client: AsyncIOMotorClient | None = None


def get_client() -> AsyncIOMotorClient:
    global _client
    if _client is None:
        _client = AsyncIOMotorClient(settings.mongodb_url)
    return _client


def get_db() -> AsyncIOMotorDatabase:
    return get_client()[settings.mongodb_db]


async def init_db() -> None:
    from app.db.admin_seed import ensure_default_admin

    db = get_db()
    await db.users.create_index("email", unique=True)
    await db.users.create_index("role")
    await db.users.update_many({"role": {"$exists": False}}, {"$set": {"role": "viewer"}})
    await ensure_default_admin()
    await db.otp_challenges.create_index("challenge_token", unique=True)
    await db.tickets.create_index("ticket_id", unique=True)
    await db.tickets.create_index("status")
    await db.tickets.create_index("created_at")
    await db.tickets.create_index([("final_triage.severity", 1)])
    await db.tickets.create_index([("status", 1), ("created_at", -1)])


async def close_db() -> None:
    global _client
    if _client is not None:
        _client.close()
        _client = None

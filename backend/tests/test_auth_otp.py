import asyncio
from datetime import datetime, timezone

from app.auth import router as auth_router
from app.auth.schemas import LoginRequest, RegisterRequest, VerifyOtpRequest
from app.core.roles import UserRole
from app.core.security import hash_otp, hash_password


class FakeCollection:
    def __init__(self):
        self.docs = []

    async def find_one(self, query):
        for doc in self.docs:
            if all(doc.get(key) == value for key, value in query.items()):
                return doc
        return None

    async def insert_one(self, doc):
        self.docs.append(doc)

    async def delete_many(self, query):
        self.docs = [
            doc for doc in self.docs if not all(doc.get(key) == value for key, value in query.items())
        ]

    async def update_one(self, query, update):
        doc = await self.find_one(query)
        if doc:
            doc.update(update.get("$set", {}))


class FakeDb:
    def __init__(self):
        self.users = FakeCollection()
        self.otp_challenges = FakeCollection()


def test_viewer_auth_otp_flow(monkeypatch):
    async def run():
        db = FakeDb()
        sent = []

        async def fake_send_otp_email(email, otp):
            sent.append((email, otp))

        monkeypatch.setattr(auth_router, "get_db", lambda: db)
        monkeypatch.setattr(auth_router, "generate_otp", lambda: "123456")
        monkeypatch.setattr(auth_router, "generate_challenge_token", lambda: "challenge-token")
        monkeypatch.setattr(auth_router, "send_otp_email", fake_send_otp_email)
        registration = await auth_router.register(
            RegisterRequest(email="reporter@example.com", password="password123")
        )
        assert registration.challenge_token == "challenge-token"
        user = await db.users.find_one({"email": "reporter@example.com"})
        assert user["role"] == UserRole.VIEWER.value
        assert sent == [("reporter@example.com", "123456")]

        login = await auth_router.login(
            LoginRequest(email="reporter@example.com", password="password123")
        )
        assert login.challenge_token == "challenge-token"
        assert sent == [
            ("reporter@example.com", "123456"),
            ("reporter@example.com", "123456"),
        ]

        token = await auth_router.verify_otp_endpoint(
            VerifyOtpRequest(challenge_token="challenge-token", otp="123456")
        )
        assert token.access_token

        challenge = await db.otp_challenges.find_one({"challenge_token": "challenge-token"})
        assert challenge["used"] is True

    asyncio.run(run())


def test_admin_sign_in_returns_token_without_otp(monkeypatch):
    async def run():
        db = FakeDb()
        db.users.docs.append(
            {
                "email": "admin@example.com",
                "password_hash": hash_password("password123"),
                "role": UserRole.ADMIN.value,
                "created_at": datetime.now(timezone.utc),
            }
        )
        monkeypatch.setattr(auth_router, "get_db", lambda: db)

        result = await auth_router.sign_in(
            LoginRequest(email="admin@example.com", password="password123")
        )
        assert result.flow == "token"
        assert result.access_token
        assert result.challenge_token is None

    asyncio.run(run())

import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings
from app.core.roles import UserRole

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(subject: str, role: UserRole) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    return jwt.encode(
        {"sub": subject, "role": role.value, "exp": expire},
        settings.secret_key,
        algorithm=ALGORITHM,
    )


def decode_access_token(token: str) -> tuple[str, UserRole] | None:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
        sub = payload.get("sub")
        if not isinstance(sub, str):
            return None
        role_raw = payload.get("role")
        role = (
            UserRole(role_raw)
            if role_raw in (UserRole.ADMIN.value, UserRole.VIEWER.value)
            else UserRole.ADMIN
        )
        return sub, role
    except (JWTError, ValueError):
        return None


def generate_otp() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def generate_challenge_token() -> str:
    return secrets.token_urlsafe(32)


def hash_otp(otp: str) -> str:
    return hashlib.sha256(otp.encode()).hexdigest()


def verify_otp(otp: str, otp_hash: str) -> bool:
    return hash_otp(otp) == otp_hash


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def ensure_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)

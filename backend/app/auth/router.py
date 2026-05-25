from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status

from app.auth.schemas import (
    CreateUserRequest,
    LoginRequest,
    LoginResponse,
    RegisterRequest,
    SignInResponse,
    TokenResponse,
    UserResponse,
    VerifyOtpRequest,
)
from app.core.config import settings
from app.core.deps import get_current_user, require_admin
from app.core.roles import UserRole
from app.core.security import (
    create_access_token,
    ensure_utc,
    generate_challenge_token,
    generate_otp,
    hash_otp,
    hash_password,
    utc_now,
    verify_otp,
    verify_password,
)
from app.core.user import CurrentUser, user_from_doc
from app.db.mongodb import get_db
from app.services.email import EmailDeliveryError, send_otp_email

router = APIRouter(prefix="/auth", tags=["auth"])


async def _user_for_credentials(email: str, password: str):
    db = get_db()
    normalized = email.lower()
    user_doc = await db.users.find_one({"email": normalized})
    if not user_doc or not verify_password(password, user_doc["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    return user_from_doc(user_doc)


async def _issue_viewer_otp(email: str) -> str:
    db = get_db()
    otp = generate_otp()
    challenge_token = generate_challenge_token()
    expires_at = utc_now() + timedelta(minutes=settings.otp_expire_minutes)

    await db.otp_challenges.delete_many({"user_email": email, "used": False})

    await db.otp_challenges.insert_one(
        {
            "challenge_token": challenge_token,
            "user_email": email,
            "otp_hash": hash_otp(otp),
            "expires_at": expires_at,
            "used": False,
        }
    )

    try:
        await send_otp_email(email, otp)
    except EmailDeliveryError as exc:
        await db.otp_challenges.delete_many({"challenge_token": challenge_token})
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Could not send OTP email. Check SMTP configuration and try again.",
        ) from exc
    return challenge_token


def _ensure_public_register_allowed() -> None:
    if not settings.allow_public_register:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Public registration is disabled. Ask an admin to create your account.",
        )


@router.post("/register", status_code=status.HTTP_201_CREATED, response_model=LoginResponse)
async def register(body: RegisterRequest):
    db = get_db()
    email = body.email.lower()
    if email == settings.admin_email.lower():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This email is reserved for the administrator account",
        )
    if await db.users.find_one({"email": email}):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    _ensure_public_register_allowed()
    await db.users.insert_one(
        {
            "email": email,
            "password_hash": hash_password(body.password),
            "role": UserRole.VIEWER.value,
            "created_at": datetime.now(timezone.utc),
        }
    )
    try:
        challenge_token = await _issue_viewer_otp(email)
    except HTTPException:
        await db.users.delete_many({"email": email, "role": UserRole.VIEWER.value})
        raise
    return LoginResponse(
        challenge_token=challenge_token,
        message="Registration successful. OTP sent to your email.",
    )


@router.post("/users", status_code=status.HTTP_201_CREATED)
async def create_user(
    body: CreateUserRequest,
    _admin: CurrentUser = Depends(require_admin),
):
    db = get_db()
    email = body.email.lower()
    if await db.users.find_one({"email": email}):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )
    if body.role == UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only one admin account is allowed",
        )

    await db.users.insert_one(
        {
            "email": email,
            "password_hash": hash_password(body.password),
            "role": body.role.value,
            "created_at": datetime.now(timezone.utc),
        }
    )
    return {"message": "User created", "email": email, "role": body.role.value}


@router.post("/sign-in", response_model=SignInResponse)
async def sign_in(body: LoginRequest):
    user = await _user_for_credentials(body.email, body.password)

    if user.role == UserRole.ADMIN:
        token = create_access_token(user.email, user.role)
        return SignInResponse(flow="token", access_token=token, message="Signed in")

    if user.role != UserRole.VIEWER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account cannot sign in",
        )

    challenge_token = await _issue_viewer_otp(user.email)
    return SignInResponse(
        flow="otp",
        challenge_token=challenge_token,
        message="OTP sent to your email",
    )


@router.post("/admin/login", response_model=TokenResponse)
async def admin_login(body: LoginRequest):
    result = await sign_in(body)
    if result.flow != "token" or not result.access_token:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin credentials required",
        )
    return TokenResponse(access_token=result.access_token)


@router.post("/login", response_model=LoginResponse)
async def login(body: LoginRequest):
    result = await sign_in(body)
    if result.flow != "otp" or not result.challenge_token:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Reporter sign-in requires email verification",
        )
    return LoginResponse(
        challenge_token=result.challenge_token,
        message=result.message,
    )


@router.post("/verify-otp", response_model=TokenResponse)
async def verify_otp_endpoint(body: VerifyOtpRequest):
    db = get_db()
    challenge = await db.otp_challenges.find_one(
        {"challenge_token": body.challenge_token, "used": False}
    )
    if not challenge:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired challenge",
        )

    if ensure_utc(challenge["expires_at"]) < utc_now():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="OTP has expired",
        )

    if not verify_otp(body.otp, challenge["otp_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid OTP",
        )

    await db.otp_challenges.update_one(
        {"challenge_token": body.challenge_token},
        {"$set": {"used": True}},
    )

    user_doc = await db.users.find_one({"email": challenge["user_email"]})
    if not user_doc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    user = user_from_doc(user_doc)
    if user.role not in (UserRole.ADMIN, UserRole.VIEWER):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account cannot sign in",
        )

    return TokenResponse(access_token=create_access_token(user.email, user.role))


@router.get("/me", response_model=UserResponse)
async def me(user: CurrentUser = Depends(get_current_user)):
    return UserResponse(email=user.email, role=user.role)

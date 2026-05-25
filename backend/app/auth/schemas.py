from typing import Literal

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.core.roles import UserRole


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    challenge_token: str
    message: str = "OTP sent to your email"


class SignInResponse(BaseModel):
    flow: Literal["token", "otp"]
    access_token: str | None = None
    challenge_token: str | None = None
    message: str = ""


class VerifyOtpRequest(BaseModel):
    challenge_token: str
    otp: str = Field(min_length=6, max_length=6, pattern=r"^\d{6}$")

    @field_validator("otp", mode="before")
    @classmethod
    def strip_otp(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip()
        return value


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    email: str
    role: UserRole


class CreateUserRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    role: UserRole = UserRole.VIEWER

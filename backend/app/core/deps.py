from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.roles import OPS_ROLES, UserRole
from app.core.security import decode_access_token
from app.core.user import CurrentUser, user_from_doc
from app.db.mongodb import get_db

bearer_scheme = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> CurrentUser:
    decoded = decode_access_token(credentials.credentials)
    if not decoded:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    email, _token_role = decoded
    db = get_db()
    user_doc = await db.users.find_one({"email": email})
    if not user_doc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user_from_doc(user_doc)


async def get_current_user_email(user: CurrentUser = Depends(get_current_user)) -> str:
    return user.email


async def require_ops_user(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    if user.role not in OPS_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Ops console access required",
        )
    return user


async def require_admin(user: CurrentUser = Depends(require_ops_user)) -> CurrentUser:
    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required for this action",
        )
    return user


async def require_reporter(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    if user.role != UserRole.VIEWER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Reporter account required for this action",
        )
    return user

from fastapi import APIRouter, Depends, HTTPException, status
from supabase import Client

from app.core.database import get_supabase
from app.core.dependencies import get_current_user_id
from app.core.security import create_access_token, hash_password, verify_password
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register(payload: RegisterRequest, db: Client = Depends(get_supabase)):
    """Register a new user with email and password.

    Checks for duplicate email, hashes the password with bcrypt, persists
    the record, and returns a JWT so the client is immediately authenticated.
    """
    existing = (
        db.table("users")
        .select("id")
        .eq("email", payload.email)
        .limit(1)
        .execute()
    )
    if existing.data:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    result = (
        db.table("users")
        .insert(
            {
                "email": payload.email,
                "password_hash": hash_password(payload.password),
            }
        )
        .execute()
    )
    user = result.data[0]
    return TokenResponse(access_token=create_access_token(user["id"]))


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, db: Client = Depends(get_supabase)):
    """Authenticate with email and password, return a JWT on success.

    Returns 401 for both unknown email and wrong password (same message)
    to avoid leaking which emails are registered.
    """
    result = (
        db.table("users")
        .select("id, password_hash")
        .eq("email", payload.email)
        .limit(1)
        .execute()
    )
    user = result.data[0] if result.data else None
    if not user or not verify_password(payload.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    return TokenResponse(access_token=create_access_token(user["id"]))


@router.get("/me", response_model=UserResponse)
async def me(
    user_id: str = Depends(get_current_user_id),
    db: Client = Depends(get_supabase),
):
    """Return basic profile info for the authenticated user."""
    result = (
        db.table("users").select("id, email").eq("id", user_id).limit(1).execute()
    )
    return result.data[0]

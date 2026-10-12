import os
import re
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

import jwt
from pwdlib import PasswordHash
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer


router = APIRouter(prefix="/api/auth", tags=["Authentication"])
password_hasher = PasswordHash.recommended()
bearer_scheme = HTTPBearer(auto_error=False)

# Use the SAME database as the existing simulator.
PROJECT_DIR = Path(__file__).resolve().parents[3]
DB_PATH = PROJECT_DIR / "data" / "simulator.db"

JWT_ALGORITHM = "HS256"
TOKEN_MINUTES = 60
STARTING_BALANCE = 10_000.0


def get_secret() -> str:
    secret = os.getenv("JWT_SECRET_KEY", "")
    if len(secret) < 32:
        raise HTTPException(
            status_code=503,
            detail="Authentication is not configured. Set JWT_SECRET_KEY.",
        )
    return secret


def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    return conn


def init_auth_db():
    """Initialize authentication and per-user simulator account tables."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL UNIQUE COLLATE NOCASE,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS simulator_accounts (
                user_id INTEGER PRIMARY KEY,
                balance REAL NOT NULL DEFAULT 10000.0,
                currency TEXT NOT NULL DEFAULT 'USD',
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)


init_auth_db()


class SignupRequest(BaseModel):
    email: str = Field(min_length=5, max_length=254)
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email: str = Field(min_length=5, max_length=254)
    password: str = Field(min_length=1, max_length=128)


def normalize_email(email: str) -> str:
    value = email.strip().lower()

    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", value):
        raise HTTPException(
            status_code=422,
            detail="Enter a valid email address.",
        )

    return value


def create_token(user_id: int, email: str) -> str:
    now = datetime.now(timezone.utc)

    payload = {
        "sub": str(user_id),
        "email": email,
        "iat": now,
        "exp": now + timedelta(minutes=TOKEN_MINUTES),
    }

    return jwt.encode(
        payload,
        get_secret(),
        algorithm=JWT_ALGORITHM,
    )


def public_user(row):
    return {
        "id": row["id"],
        "email": row["email"],
        "created_at": row["created_at"],
    }


def current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
):
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Please log in to continue.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = jwt.decode(
            credentials.credentials,
            get_secret(),
            algorithms=[JWT_ALGORITHM],
        )
        user_id = int(payload["sub"])

    except HTTPException:
        raise

    except (jwt.InvalidTokenError, ValueError, KeyError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    with get_db() as conn:
        row = conn.execute(
            "SELECT id, email, created_at FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()

    if row is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account not found.",
        )

    return public_user(row)


@router.post("/signup", status_code=status.HTTP_201_CREATED)
def signup(data: SignupRequest):
    email = normalize_email(data.email)

    # Fail closed if authentication is not configured.
    get_secret()

    password_hash = password_hasher.hash(data.password)
    created_at = datetime.now(timezone.utc).isoformat()

    try:
        with get_db() as conn:
            cursor = conn.execute(
                """
                INSERT INTO users (email, password_hash, created_at)
                VALUES (?, ?, ?)
                """,
                (email, password_hash, created_at),
            )

            user_id = cursor.lastrowid

            # Give every newly registered user an independent demo balance.
            # INSERT OR IGNORE prevents an existing balance from being reset.
            conn.execute(
                """
                INSERT OR IGNORE INTO simulator_accounts
                    (user_id, balance, currency)
                VALUES (?, ?, 'USD')
                """,
                (user_id, STARTING_BALANCE),
            )

    except sqlite3.IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        )

    return {
        "message": "Account created successfully.",
        "user": {
            "id": user_id,
            "email": email,
            "created_at": created_at,
        },
        "access_token": create_token(user_id, email),
        "token_type": "bearer",
    }


@router.post("/login")
def login(data: LoginRequest):
    email = normalize_email(data.email)

    with get_db() as conn:
        row = conn.execute(
            """
            SELECT id, email, password_hash, created_at
            FROM users
            WHERE email = ?
            """,
            (email,),
        ).fetchone()

    if row is None or not password_hasher.verify(
        data.password,
        row["password_hash"],
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return {
        "message": "Login successful.",
        "user": public_user(row),
        "access_token": create_token(row["id"], row["email"]),
        "token_type": "bearer",
    }


@router.get("/me")
def me(user=Depends(current_user)):
    return {"user": user}
import secrets
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
import bcrypt

from core.trade_repository import (
    get_connection,
    _execute,
    _adapt_query,
    _fetch_rows,
    _fetch_one,
    IS_POSTGRES,
)

logger = logging.getLogger(__name__)

SESSION_DURATION_DAYS = 30

class UserRepository:

    def _get_connection(self):
        return get_connection()

    def create_user(
        self,
        email: str,
        password: str,
        name: str,
        is_admin: bool = False,
    ) -> Optional[Dict]:

        if self.get_user_by_email(email):
            logger.warning(f"Registration attempt with existing email: {email}")
            return None

        password_bytes = password.encode("utf-8")
        salt = bcrypt.gensalt(rounds=12)   # 12 rounds = good security/speed balance
        password_hash = bcrypt.hashpw(password_bytes, salt).decode("utf-8")

        user_id = f"u_{secrets.token_hex(16)}"
        now = datetime.now(timezone.utc).isoformat()

        conn = self._get_connection()
        try:
            sql = _adapt_query("""
                INSERT INTO users (
                    id, email, password_hash, name,
                    plan, is_admin, created_at
                ) VALUES (?, ?, ?, ?, 'free', ?, ?)
            """)
            _execute(conn, sql, (
                user_id, email.lower().strip(),
                password_hash, name,
                int(is_admin), now,
            ))
            conn.commit()
            logger.info(f"Created user: {email}")
            return self.get_user_by_id(user_id)
        except Exception as e:
            logger.warning(f"create_user failed: {e}")
            try:
                conn.rollback()
            except Exception:
                pass
            return None
        finally:
            conn.close()

    def get_user_by_email(self, email: str) -> Optional[Dict]:

        conn = self._get_connection()
        cursor = _execute(
            conn,
            _adapt_query("SELECT * FROM users WHERE email = ?"),
            (email.lower().strip(),)
        )
        row = _fetch_one(cursor)
        conn.close()
        return row

    def get_user_by_id(self, user_id: str) -> Optional[Dict]:
        conn = self._get_connection()
        cursor = _execute(
            conn,
            _adapt_query("SELECT * FROM users WHERE id = ?"),
            (user_id,)
        )
        row = _fetch_one(cursor)
        conn.close()
        return row

    def update_last_login(self, user_id: str) -> None:
        conn = self._get_connection()
        try:
            _execute(
                conn,
                _adapt_query("UPDATE users SET last_login = ? WHERE id = ?"),
                (datetime.now(timezone.utc).isoformat(), user_id)
            )
            conn.commit()
        finally:
            conn.close()

    def get_all_users(self) -> list:
        conn = self._get_connection()
        cursor = _execute(
            conn,
            "SELECT id, email, name, plan, created_at, last_login "
            "FROM users ORDER BY created_at DESC"
        )
        users = _fetch_rows(cursor)
        conn.close()
        return users

class AuthEngine:

    def __init__(self):
        self.user_repo = UserRepository()

    def register(
        self,
        email: str,
        password: str,
        name: str,
    ) -> Dict[str, Any]:

        email = email.lower().strip()
        name = name.strip()

        if not email or "@" not in email:
            return {
                "success": False,
                "error": "Please enter a valid email address"
            }

        if not name or len(name) < 2:
            return {
                "success": False,
                "error": "Please enter your full name (minimum 2 characters)"
            }

        if len(password) < 8:
            return {
                "success": False,
                "error": "Password must be at least 8 characters"
            }

        if not any(c.isdigit() for c in password):
            return {
                "success": False,
                "error": "Password must contain at least one number"
            }

        user = self.user_repo.create_user(email, password, name)

        if not user:
            return {
                "success": False,
                "error": "An account with this email already exists"
            }

        token = self._create_session(user["id"])

        logger.info(f"New user registered: {email}")
        return {
            "success": True,
            "user": user,
            "token": token,
        }

    def login(
        self,
        email: str,
        password: str,
    ) -> Dict[str, Any]:

        email = email.lower().strip()

        user = self.user_repo.get_user_by_email(email)

        if not user:

            logger.warning(f"Failed login attempt for email: {email}")
            return {
                "success": False,
                "error": "Invalid email or password"
            }

        password_bytes = password.encode("utf-8")
        stored_hash = user["password_hash"].encode("utf-8")
        password_valid = bcrypt.checkpw(password_bytes, stored_hash)

        if not password_valid:
            logger.warning(f"Wrong password for email: {email}")
            return {
                "success": False,
                "error": "Invalid email or password"
            }
        
        token = self._create_session(user["id"])

        self.user_repo.update_last_login(user["id"])

        logger.info(f"User logged in: {email}")
        return {
            "success": True,
            "user": user,
            "token": token,
        }

    def validate_session(
        self,
        token: str
    ) -> Optional[Dict]:

        if not token:
            return None

        conn = get_connection()

        cursor = _execute(
            conn,
            _adapt_query("""
                SELECT s.*, u.id as user_id, u.email, u.name,
                    u.plan, u.is_admin
                FROM sessions s
                JOIN users u ON s.user_id = u.id
                WHERE s.token = ?
            """),
            (token,)
        )

        session = _fetch_one(cursor)
        conn.close()

        if not session:
            return None

        expires_at = datetime.fromisoformat(
            session["expires_at"].split("+")[0]
        ).replace(tzinfo=timezone.utc)

        if datetime.now(timezone.utc) > expires_at:
            self._delete_session(token)
            logger.info("Expired session deleted")
            return None

        return {
            "id": session["user_id"],
            "email": session["email"],
            "name": session["name"],
            "plan": session["plan"],
            "is_admin": bool(session["is_admin"]),
        }

    def logout(self, token: str) -> None:
        """Deletes the session token — user is logged out."""
        self._delete_session(token)
        logger.info("User logged out")

    def _create_session(self, user_id: str) -> str:
        """
        Creates a new session token for a user.

        secrets.token_urlsafe(32) generates a 43-character
        cryptographically random string. This is the session token
        stored in the browser cookie.

        Probability of guessing: 1 in 2^192 — practically impossible.
        """
        token = secrets.token_urlsafe(32)
        now = datetime.now(timezone.utc)
        expires = now + timedelta(days=SESSION_DURATION_DAYS)

        conn = get_connection()
        try:
            _execute(
                conn,
                _adapt_query("""
                    INSERT INTO sessions (user_id, token, created_at, expires_at)
                    VALUES (?, ?, ?, ?)
                """),
                (
                    user_id,
                    token,
                    now.isoformat(),
                    expires.isoformat(),
                )
            )
            conn.commit()
        finally:
            conn.close()

        return token

    def _delete_session(self, token: str) -> None:
        
        conn = get_connection()
        try:
            _execute(
                conn,
                _adapt_query("DELETE FROM sessions WHERE token = ?"),
                (token,)
            )
            conn.commit()
        finally:
            conn.close()
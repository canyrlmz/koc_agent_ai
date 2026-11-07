"""Kullanıcılar, roller ve oturumlar.

Roller:
  admin    Yönetici: her şeyi görür, kullanıcıları yönetir
  koc      Koç: yalnızca kendisine atanmış danışanları görür ve yönetir
  danisan  Danışan: yalnızca kendi gelişimini görür (koç değerlendirmesi ve transkript hariç)
  kurum    Kurum yöneticisi: yalnızca kendi kurumunun anonim, toplu panelini görür

Şifreler scrypt ile tuzlanarak saklanır; oturum, HttpOnly çerezde rastgele bir anahtardır.
"""
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta

from . import db

ROLES = ("admin", "koc", "danisan", "kurum")
ROLE_LABELS = {"admin": "Yönetici", "koc": "Koç", "danisan": "Danışan", "kurum": "Kurum yöneticisi"}
SESSION_DAYS = 14
COOKIE = "koc_oturum"

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT NOT NULL UNIQUE COLLATE NOCASE,
    name TEXT NOT NULL,
    role TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    client_id INTEGER REFERENCES clients(id),
    organization_id INTEGER REFERENCES organizations(id),
    is_demo INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS auth_sessions (
    token_hash TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    expires_at TEXT NOT NULL
);
"""


# --- Şifre ----------------------------------------------------------------------


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1)
    return f"scrypt${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        _, salt_hex, digest_hex = stored.split("$")
    except ValueError:
        return False
    digest = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt_hex), n=2**14, r=8, p=1)
    return hmac.compare_digest(digest.hex(), digest_hex)


# --- Kullanıcılar ---------------------------------------------------------------

_PUBLIC = "id, email, name, role, client_id, organization_id, is_demo, created_at"


def user_count() -> int:
    return db.all_rows("SELECT COUNT(*) AS n FROM users WHERE is_demo = 0")[0]["n"]


def create_user(email: str, name: str, role: str, password: str, client_id: int | None = None,
                organization_id: int | None = None, is_demo: bool = False) -> dict:
    with db.connect() as conn:
        cur = conn.execute(
            """INSERT INTO users (email, name, role, password_hash, client_id, organization_id, is_demo, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (email.strip().lower(), name.strip(), role, hash_password(password), client_id, organization_id,
             int(is_demo), datetime.now().isoformat(timespec="seconds")),
        )
        user_id = cur.lastrowid
    return get_user(user_id)  # kayıt işlendikten (commit) sonra oku


def get_user(user_id: int) -> dict | None:
    rows = db.all_rows(f"SELECT {_PUBLIC} FROM users WHERE id = ?", (user_id,))
    return rows[0] if rows else None


def find_by_email(email: str) -> dict | None:
    rows = db.all_rows("SELECT * FROM users WHERE email = ?", (email.strip().lower(),))
    return rows[0] if rows else None


def list_users() -> list[dict]:
    return db.all_rows(
        f"""SELECT u.{_PUBLIC.replace(', ', ', u.')}, c.name AS client_name, o.name AS organization_name
            FROM users u LEFT JOIN clients c ON c.id = u.client_id
            LEFT JOIN organizations o ON o.id = u.organization_id ORDER BY u.role, u.name"""
    )


def user_for_client(client_id: int) -> dict | None:
    rows = db.all_rows(f"SELECT {_PUBLIC} FROM users WHERE client_id = ? AND role = 'danisan'", (client_id,))
    return rows[0] if rows else None


def set_password(user_id: int, password: str) -> None:
    db._update("users", user_id, {"password_hash": hash_password(password)})
    with db.connect() as conn:  # şifre değişince açık oturumlar kapanır
        conn.execute("DELETE FROM auth_sessions WHERE user_id = ?", (user_id,))


def delete_user(user_id: int) -> None:
    with db.connect() as conn:
        conn.execute("DELETE FROM auth_sessions WHERE user_id = ?", (user_id,))
        conn.execute("DELETE FROM users WHERE id = ?", (user_id,))


# --- Oturumlar ------------------------------------------------------------------


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def create_session(user_id: int) -> str:
    token = secrets.token_urlsafe(32)
    expires = (datetime.now() + timedelta(days=SESSION_DAYS)).isoformat(timespec="seconds")
    with db.connect() as conn:
        conn.execute("INSERT INTO auth_sessions (token_hash, user_id, expires_at) VALUES (?, ?, ?)",
                     (_token_hash(token), user_id, expires))
    return token


def user_from_token(token: str | None) -> dict | None:
    if not token:
        return None
    rows = db.all_rows(
        f"""SELECT u.{_PUBLIC.replace(', ', ', u.')} FROM auth_sessions s JOIN users u ON u.id = s.user_id
            WHERE s.token_hash = ? AND s.expires_at > ?""",
        (_token_hash(token), datetime.now().isoformat(timespec="seconds")),
    )
    return rows[0] if rows else None


def end_session(token: str | None) -> None:
    if token:
        with db.connect() as conn:
            conn.execute("DELETE FROM auth_sessions WHERE token_hash = ?", (_token_hash(token),))


# --- Erişim kuralları --------------------------------------------------------------


def can_manage_client(user: dict, client: dict) -> bool:
    """Koç paneli erişimi (seanslar, ICF, rapor, ajan)."""
    if user["role"] == "admin":
        return True
    return user["role"] == "koc" and client.get("coach_id") == user["id"]


def can_view_client_portal(user: dict, client: dict) -> bool:
    """Danışanın kendi portalı."""
    return can_manage_client(user, client) or (user["role"] == "danisan" and user["client_id"] == client["id"])

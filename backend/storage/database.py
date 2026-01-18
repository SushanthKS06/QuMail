import json
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

import aiosqlite

from config import settings

logger = logging.getLogger(__name__)

_db_connection: Optional[aiosqlite.Connection] = None


async def get_db() -> aiosqlite.Connection:
    global _db_connection
    if _db_connection is None:
        _db_connection = await aiosqlite.connect(settings.db_path)
        _db_connection.row_factory = aiosqlite.Row
    return _db_connection


async def init_database() -> None:
    db = await get_db()
    
    await db.execute("""
        CREATE TABLE IF NOT EXISTS accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            provider TEXT DEFAULT 'gmail',
            access_token TEXT,
            refresh_token TEXT,
            expires_at TIMESTAMP,
            connected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    await db.execute("""
        CREATE TABLE IF NOT EXISTS known_recipients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            is_qumail_user BOOLEAN DEFAULT 0,
            public_key TEXT,
            public_key_fingerprint TEXT,
            supported_levels TEXT DEFAULT '[4]',
            last_seen TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    await db.execute("""
        CREATE TABLE IF NOT EXISTS drafts (
            id TEXT PRIMARY KEY,
            to_addrs TEXT,
            cc_addrs TEXT,
            subject TEXT,
            body TEXT,
            security_level INTEGER DEFAULT 2,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    await db.execute("""
        CREATE TABLE IF NOT EXISTS sent_emails (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            message_id TEXT UNIQUE,
            from_addr TEXT,
            to_addrs TEXT,
            cc_addrs TEXT,
            subject TEXT,
            body_hash TEXT,
            security_level INTEGER,
            key_id TEXT,
            sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    await db.execute("""
        CREATE TABLE IF NOT EXISTS audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_type TEXT NOT NULL,
            event_data TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    await db.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    await db.commit()
    logger.info("Database schema initialized")


async def store_oauth_tokens(
    email: str,
    access_token: str,
    refresh_token: Optional[str],
    expires_in: int,
    provider: str = "gmail",
) -> None:
    db = await get_db()
    
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
    
    await db.execute("""
        INSERT INTO accounts (email, provider, access_token, refresh_token, expires_at)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(email) DO UPDATE SET
            provider = excluded.provider,
            access_token = excluded.access_token,
            refresh_token = COALESCE(excluded.refresh_token, accounts.refresh_token),
            expires_at = excluded.expires_at
    """, (email, provider, access_token, refresh_token, expires_at.isoformat()))
    
    await db.commit()
    logger.info("Stored OAuth tokens for %s (%s)", email, provider)


async def get_oauth_tokens(email: str) -> Optional[Dict[str, Any]]:
    db = await get_db()
    
    cursor = await db.execute(
        "SELECT * FROM accounts WHERE email = ?",
        (email,)
    )
    row = await cursor.fetchone()
    
    if row:
        return {
            "email": row["email"],
            "access_token": row["access_token"],
            "refresh_token": row["refresh_token"],
            "expires_at": row["expires_at"],
        }
    return None


async def get_stored_accounts() -> List[Dict[str, Any]]:
    db = await get_db()
    
    cursor = await db.execute("SELECT * FROM accounts")
    rows = await cursor.fetchall()
    
    return [
        {
            "email": row["email"],
            "provider": row["provider"],
            "connected_at": row["connected_at"],
        }
        for row in rows
    ]


async def get_known_recipient(email: str) -> Optional[Dict[str, Any]]:
    db = await get_db()
    
    cursor = await db.execute(
        "SELECT * FROM known_recipients WHERE email = ?",
        (email,)
    )
    row = await cursor.fetchone()
    
    if row:
        return {
            "email": row["email"],
            "is_qumail_user": bool(row["is_qumail_user"]),
            "public_key": row["public_key"],
            "public_key_fingerprint": row["public_key_fingerprint"],
            "supported_levels": json.loads(row["supported_levels"]),
            "last_seen": row["last_seen"],
        }
    return None


async def store_known_recipient(
    email: str,
    public_key: Optional[str] = None,
    supported_levels: Optional[List[int]] = None,
) -> None:
    db = await get_db()
    
    import hashlib
    fingerprint = None
    if public_key:
        fingerprint = "SHA256:" + hashlib.sha256(public_key.encode()).hexdigest()[:16]
    
    levels = json.dumps(supported_levels or [4])
    
    await db.execute("""
        INSERT INTO known_recipients (email, is_qumail_user, public_key, public_key_fingerprint, supported_levels, last_seen)
        VALUES (?, 1, ?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(email) DO UPDATE SET
            is_qumail_user = 1,
            public_key = COALESCE(excluded.public_key, known_recipients.public_key),
            public_key_fingerprint = COALESCE(excluded.public_key_fingerprint, known_recipients.public_key_fingerprint),
            supported_levels = excluded.supported_levels,
            last_seen = CURRENT_TIMESTAMP
    """, (email, public_key, fingerprint, levels))
    
    await db.commit()


async def save_email_draft(
    draft_id: str,
    to: List[str],
    cc: List[str],
    subject: str,
    body: str,
    security_level: int,
) -> None:
    db = await get_db()
    
    await db.execute("""
        INSERT INTO drafts (id, to_addrs, cc_addrs, subject, body, security_level)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            to_addrs = excluded.to_addrs,
            cc_addrs = excluded.cc_addrs,
            subject = excluded.subject,
            body = excluded.body,
            security_level = excluded.security_level,
            updated_at = CURRENT_TIMESTAMP
    """, (draft_id, json.dumps(to), json.dumps(cc), subject, body, security_level))
    
    await db.commit()


async def save_sent_email(
    message_id: str,
    from_addr: str,
    to_addrs: List[str],
    cc_addrs: List[str],
    subject: str,
    body: str,
    security_level: int,
    key_id: Optional[str],
) -> None:
    db = await get_db()
    
    import hashlib
    body_hash = hashlib.sha256(body.encode()).hexdigest()
    
    await db.execute("""
        INSERT INTO sent_emails (message_id, from_addr, to_addrs, cc_addrs, subject, body_hash, security_level, key_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        message_id,
        from_addr,
        json.dumps(to_addrs),
        json.dumps(cc_addrs),
        subject,
        body_hash,
        security_level,
        key_id,
    ))
    
    await db.commit()


async def log_audit_event(event_type: str, event_data: Dict[str, Any]) -> None:
    db = await get_db()
    
    await db.execute(
        "INSERT INTO audit_log (event_type, event_data) VALUES (?, ?)",
        (event_type, json.dumps(event_data))
    )
    
    await db.commit()


async def get_settings() -> Dict[str, Any]:
    db = await get_db()
    cursor = await db.execute("SELECT key, value FROM settings")
    rows = await cursor.fetchall()
    
    settings_dict = {}
    for row in rows:
        try:
            settings_dict[row["key"]] = json.loads(row["value"])
        except json.JSONDecodeError:
            settings_dict[row["key"]] = row["value"]
            
    return settings_dict


async def save_setting(key: str, value: Any) -> None:
    db = await get_db()
    
    await db.execute("""
        INSERT INTO settings (key, value, updated_at)
        VALUES (?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(key) DO UPDATE SET
            value = excluded.value,
            updated_at = CURRENT_TIMESTAMP
    """, (key, json.dumps(value)))
    
    await db.commit()

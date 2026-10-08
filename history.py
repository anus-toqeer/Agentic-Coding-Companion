
import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = DATA_DIR / "chats.db"


def connect():
    connection = sqlite3.connect(DB_PATH, timeout=30)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA busy_timeout = 30000")
    return connection


def now():
    return datetime.now(timezone.utc).isoformat()


def initialize_database():
    with connect() as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)

        db.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (conversation_id)
                    REFERENCES conversations(id)
            )
        """)

        db.execute("""
            CREATE TABLE IF NOT EXISTS activity (
                conversation_id TEXT PRIMARY KEY,
                content TEXT NOT NULL
            )
        """)


def create_conversation(title="New Chat"):
    conversation_id = str(uuid.uuid4())
    timestamp = now()

    with connect() as db:
        db.execute(
            """
            INSERT INTO conversations
            (id, title, created_at, updated_at)
            VALUES (?, ?, ?, ?)
            """,
            (conversation_id, title, timestamp, timestamp)
        )

    return conversation_id


def list_conversations():
    with connect() as db:
        rows = db.execute("""
            SELECT * FROM conversations
            ORDER BY updated_at DESC
        """).fetchall()

    return [dict(row) for row in rows]


def conversation_exists(conversation_id):
    with connect() as db:
        row = db.execute(
            "SELECT 1 FROM conversations WHERE id = ?",
            (conversation_id,)
        ).fetchone()

    return row is not None


def rename_conversation(conversation_id, title):
    title = title.strip() or "New Chat"

    with connect() as db:
        db.execute(
            """
            UPDATE conversations
            SET title = ?, updated_at = ?
            WHERE id = ?
            """,
            (title, now(), conversation_id)
        )


def save_message(conversation_id, role, content):
    with connect() as db:
        db.execute(
            """
            INSERT INTO messages
            (conversation_id, role, content, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (conversation_id, role, str(content), now())
        )

        db.execute(
            """
            UPDATE conversations
            SET updated_at = ?
            WHERE id = ?
            """,
            (now(), conversation_id)
        )


def load_messages(conversation_id):
    with connect() as db:
        rows = db.execute(
            """
            SELECT role, content FROM messages
            WHERE conversation_id = ?
            ORDER BY id ASC
            """,
            (conversation_id,)
        ).fetchall()

    return [dict(row) for row in rows]


def save_activity(conversation_id, activity):
    with connect() as db:
        db.execute(
            """
            INSERT INTO activity (conversation_id, content)
            VALUES (?, ?)
            ON CONFLICT(conversation_id)
            DO UPDATE SET content = excluded.content
            """,
            (conversation_id, json.dumps(activity, default=str))
        )


def load_activity(conversation_id):
    with connect() as db:
        row = db.execute(
            "SELECT content FROM activity WHERE conversation_id = ?",
            (conversation_id,)
        ).fetchone()

    return json.loads(row["content"]) if row else []


def delete_conversation(conversation_id):
    with connect() as db:
        db.execute(
            "DELETE FROM messages WHERE conversation_id = ?",
            (conversation_id,)
        )
        db.execute(
            "DELETE FROM activity WHERE conversation_id = ?",
            (conversation_id,)
        )
        db.execute(
            "DELETE FROM conversations WHERE id = ?",
            (conversation_id,)
        )


initialize_database()

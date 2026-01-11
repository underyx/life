import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel

from life.config import settings

T = TypeVar("T", bound=BaseModel)


def get_db_path() -> Path:
    return Path(settings.data_dir) / "life.db"


def init_db() -> None:
    """Initialize database with required tables."""
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS shipments (
                id TEXT PRIMARY KEY,
                data JSON NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        conn.commit()


@contextmanager
def get_connection():
    """Get a database connection."""
    db_path = get_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def save(table: str, model: BaseModel) -> None:
    """Save a Pydantic model to the database."""
    now = datetime.now(timezone.utc).isoformat()
    data = model.model_dump(mode="json")
    model_id = data.get("id")

    with get_connection() as conn:
        # Check if exists
        existing = conn.execute(
            f"SELECT id FROM {table} WHERE id = ?", (model_id,)
        ).fetchone()

        if existing:
            conn.execute(
                f"UPDATE {table} SET data = ?, updated_at = ? WHERE id = ?",
                (json.dumps(data), now, model_id),
            )
        else:
            conn.execute(
                f"INSERT INTO {table} (id, data, created_at, updated_at) VALUES (?, ?, ?, ?)",
                (model_id, json.dumps(data), now, now),
            )
        conn.commit()


def load(table: str, model_id: str, model_class: type[T]) -> T | None:
    """Load a model by ID."""
    with get_connection() as conn:
        row = conn.execute(
            f"SELECT data FROM {table} WHERE id = ?", (model_id,)
        ).fetchone()
        if row:
            return model_class.model_validate_json(row["data"])
        return None


def load_all(table: str, model_class: type[T]) -> list[T]:
    """Load all models from a table."""
    with get_connection() as conn:
        rows = conn.execute(f"SELECT data FROM {table} ORDER BY created_at DESC").fetchall()
        return [model_class.model_validate_json(row["data"]) for row in rows]


def delete(table: str, model_id: str) -> bool:
    """Delete a model by ID."""
    with get_connection() as conn:
        cursor = conn.execute(f"DELETE FROM {table} WHERE id = ?", (model_id,))
        conn.commit()
        return cursor.rowcount > 0

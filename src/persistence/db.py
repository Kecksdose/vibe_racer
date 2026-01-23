import sqlite3
from pathlib import Path


def init_db(path: Path) -> None:
    with sqlite3.connect(path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS best_times (
                track_id TEXT PRIMARY KEY,
                best_time_ms INTEGER NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS creator_times (
                track_id TEXT PRIMARY KEY,
                creator_time_ms INTEGER NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS creator_beaten (
                track_id TEXT PRIMARY KEY,
                beaten INTEGER NOT NULL
            )
            """
        )


def save_best_time(path: Path, track_id: str, best_time_ms: int) -> None:
    with sqlite3.connect(path) as conn:
        conn.execute(
            """
            INSERT INTO best_times (track_id, best_time_ms)
            VALUES (?, ?)
            ON CONFLICT(track_id) DO UPDATE SET best_time_ms = excluded.best_time_ms
            """,
            (track_id, best_time_ms),
        )


def load_best_time(path: Path, track_id: str) -> int | None:
    with sqlite3.connect(path) as conn:
        row = conn.execute(
            "SELECT best_time_ms FROM best_times WHERE track_id = ?",
            (track_id,),
        ).fetchone()
    if row is None:
        return None
    return int(row[0])


def save_creator_time(path: Path, track_id: str, creator_time_ms: int) -> None:
    with sqlite3.connect(path) as conn:
        conn.execute(
            """
            INSERT INTO creator_times (track_id, creator_time_ms)
            VALUES (?, ?)
            ON CONFLICT(track_id) DO UPDATE SET creator_time_ms = excluded.creator_time_ms
            """,
            (track_id, creator_time_ms),
        )


def load_creator_time(path: Path, track_id: str) -> int | None:
    with sqlite3.connect(path) as conn:
        row = conn.execute(
            "SELECT creator_time_ms FROM creator_times WHERE track_id = ?",
            (track_id,),
        ).fetchone()
    if row is None:
        return None
    return int(row[0])


def save_creator_beaten(path: Path, track_id: str, beaten: bool) -> None:
    with sqlite3.connect(path) as conn:
        conn.execute(
            """
            INSERT INTO creator_beaten (track_id, beaten)
            VALUES (?, ?)
            ON CONFLICT(track_id) DO UPDATE SET beaten = excluded.beaten
            """,
            (track_id, int(beaten)),
        )


def load_creator_beaten(path: Path, track_id: str) -> bool:
    with sqlite3.connect(path) as conn:
        row = conn.execute(
            "SELECT beaten FROM creator_beaten WHERE track_id = ?",
            (track_id,),
        ).fetchone()
    if row is None:
        return False
    return bool(row[0])


def clear_creator_beaten(path: Path, track_id: str) -> None:
    with sqlite3.connect(path) as conn:
        conn.execute("DELETE FROM creator_beaten WHERE track_id = ?", (track_id,))


def clear_best_time(path: Path, track_id: str) -> None:
    with sqlite3.connect(path) as conn:
        conn.execute("DELETE FROM best_times WHERE track_id = ?", (track_id,))


def clear_all_best_times(path: Path) -> None:
    with sqlite3.connect(path) as conn:
        conn.execute("DELETE FROM best_times")


def clear_all_creator_beaten(path: Path) -> None:
    with sqlite3.connect(path) as conn:
        conn.execute("DELETE FROM creator_beaten")

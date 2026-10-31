import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
DB_PATH = Path(os.getenv("LOOPLAB_DB", DATA_DIR / "looplab.sqlite3"))


@contextmanager
def connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=30, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def now():
    return datetime.now(timezone.utc).isoformat()


def init_db():
    with connect() as db:
        db.execute("""CREATE TABLE IF NOT EXISTS experiments (
            id TEXT PRIMARY KEY, parent_id TEXT, config TEXT NOT NULL,
            change_note TEXT NOT NULL, rationale TEXT NOT NULL,
            status TEXT NOT NULL, accuracy REAL, loss REAL, duration_seconds REAL,
            is_best INTEGER NOT NULL DEFAULT 0, promoted INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL,
            finished_at TEXT, error TEXT, checkpoint TEXT)""")
        columns = {row[1] for row in db.execute("PRAGMA table_info(experiments)")}
        if "promoted" not in columns:
            db.execute("ALTER TABLE experiments ADD COLUMN promoted INTEGER NOT NULL DEFAULT 0")


def decode(row):
    if not row:
        return None
    item = dict(row)
    item["config"] = json.loads(item["config"])
    item["is_best"] = bool(item["is_best"])
    item["promoted"] = bool(item.get("promoted", item["is_best"]))
    return item


def all_runs():
    with connect() as db:
        rows = db.execute("SELECT * FROM experiments ORDER BY created_at ASC").fetchall()
    return [decode(row) for row in rows]


def get_run(run_id):
    with connect() as db:
        return decode(db.execute("SELECT * FROM experiments WHERE id=?", (run_id,)).fetchone())


def best_run():
    with connect() as db:
        return decode(db.execute("SELECT * FROM experiments WHERE is_best=1 ORDER BY accuracy DESC LIMIT 1").fetchone())


def create_run(run_id, parent_id, config, change_note, rationale):
    with connect() as db:
        db.execute("INSERT INTO experiments(id,parent_id,config,change_note,rationale,status,created_at) VALUES(?,?,?,?,?,?,?)",
                   (run_id, parent_id, json.dumps(config), change_note, rationale, "queued", now()))


def update_run(run_id, **values):
    if not values:
        return
    columns = ",".join(f"{key}=?" for key in values)
    params = list(values.values()) + [run_id]
    with connect() as db:
        db.execute(f"UPDATE experiments SET {columns} WHERE id=?", params)


def set_promoted(run_id):
    with connect() as db:
        db.execute("UPDATE experiments SET is_best=0")
        db.execute("UPDATE experiments SET is_best=1 WHERE id=?", (run_id,))


def is_running():
    with connect() as db:
        return db.execute("SELECT 1 FROM experiments WHERE status IN ('queued','running') LIMIT 1").fetchone() is not None

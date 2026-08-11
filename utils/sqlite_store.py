import uuid
import sqlite3
from pathlib import Path
from threading import Lock
from datetime import datetime, timezone
from utils.logging_setup import configure_logging

logger = configure_logging("SQLiteStore")


class SQLiteStore:
    def __init__(self, db_path: str = "logs/progress.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()
        self._init_schema()

    def _now_iso(self) -> str:
        return datetime.now(timezone.utc).isoformat(timespec="seconds")

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path.as_posix())
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        return conn

    def _init_schema(self) -> None:
        with self._lock, self._connect() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS tasks (
                    run_id TEXT PRIMARY KEY,
                    query TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    finished_at TEXT,
                    successful INTEGER CHECK (successful IN (0, 1))
                );

                CREATE TABLE IF NOT EXISTS progress (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id TEXT NOT NULL,
                    node TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    finished_at TEXT,
                    final_context TEXT,
                    successful INTEGER CHECK (successful IN (0, 1)),
                    FOREIGN KEY(run_id) REFERENCES tasks(run_id)
                );

                CREATE TABLE IF NOT EXISTS pe_ttm (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                stock_code TEXT NOT NULL,
                pe_ttm_x100 INTEGER NOT NULL,
                date TEXT NOT NULL,
                CHECK (length("date") = 10 AND date("date") IS NOT NULL),
                UNIQUE (stock_code, date)
                );

                CREATE INDEX IF NOT EXISTS idx_runid_id
                ON progress (run_id, id);

                CREATE INDEX IF NOT EXISTS idx_runid_node_id
                ON progress(run_id, node, id);

                CREATE INDEX IF NOT EXISTS idx_pe_ttm
                ON pe_ttm (stock_code, date);
                """)

    def start_run(self, query: str) -> str:
        run_id = uuid.uuid4().hex
        now = self._now_iso()
        with self._lock, self._connect() as conn:
            conn.execute(
                "INSERT INTO tasks(run_id, query, created_at) VALUES (?, ?, ?)",
                [run_id, query, now],
            )
        logger.info(f"Started new run with ID: {run_id} for query: {query}")
        return run_id

    def finish_run(self, run_id: str, status_code: int | None = None) -> None:
        now = self._now_iso()

        if status_code is None:
            with self._lock, self._connect() as conn:
                cur = conn.execute(
                    """
                        SELECT
                            CASE
                                WHEN COUNT(*) = 0 THEN 0
                                WHEN SUM(CASE WHEN successful = 1 THEN 1 ELSE 0 END) = COUNT(*) THEN 1
                                ELSE 0
                            END AS all_successful
                        FROM progress
                        WHERE run_id = ?
                        """,
                    [run_id],
                ).fetchone()
            status_code = 1 if cur["all_successful"] == 1 else 0

        with self._lock, self._connect() as conn:
            conn.execute(
                """
                UPDATE tasks SET finished_at = ?, successful = ? WHERE run_id = ?
                """,
                [now, status_code, run_id],
            )

    def start_node(self, run_id: str, node: str) -> int:
        now = self._now_iso()
        with self._lock, self._connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO progress(run_id, node, created_at)
                VALUES (?, ?, ?)
                """,
                [run_id, node, now],
            )
            return int(cur.lastrowid)

    def finish_node(self, run_id: str, node: str, final_context: str | dict, status_code: int) -> None:
        now = self._now_iso()
        final_context = final_context if isinstance(final_context, str) else str(final_context)
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                UPDATE progress
                SET finished_at = ?, final_context = ?, successful = ?
                WHERE id = (SELECT id FROM progress WHERE run_id = ? AND node =? ORDER BY id DESC LIMIT 1)
                """,
                [now, final_context, status_code, run_id, node],
            )

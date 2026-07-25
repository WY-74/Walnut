import uuid
import sqlite3
from pathlib import Path
from threading import Lock
from datetime import datetime, timezone
from utils.logging_setup import configure_logging

logger = configure_logging("SQLiteStore")


class SQLiteStore:
    def __init__(self, db_path: str = "logs/progress.db", max_chars: int = 1024):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.max_chars = max_chars
        self._lock = Lock()
        self._init_schema()

    def _now_iso(self) -> str:
        return datetime.now(timezone.utc).isoformat(timespec="seconds")

    def _summarize(self, text: str) -> str:
        cleaned = " ".join(str(text).split())
        if len(cleaned) <= self.max_chars:
            return cleaned
        return cleaned[: self.max_chars] + " ..."

    def _format_rows(self, rows, max_chars: int) -> str:
        if not rows:
            return "无"

        lines = []
        used = 0
        for i, row in enumerate(rows):
            line = f"{i}. [{row['node']}] {row['summary_text']}"
            if used + len(line) + 1 > max_chars:
                break
            lines.append(line)
            used += len(line) + 1

        return "\n".join(lines) if lines else "无"

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

                CREATE INDEX IF NOT EXISTS idx_runid_id
                ON progress (run_id, id);

                CREATE INDEX IF NOT EXISTS idx_runid_node_id
                ON progress(run_id, node, id);
                """)

    def start_run(self, query: str) -> str:
        run_id = uuid.uuid4().hex
        now = self._now_iso()
        with self._lock, self._connect() as conn:
            conn.execute(
                "INSERT INTO tasks(run_id, query, created_at) VALUES (?, ?, ?)",
                (run_id, query, now),
            )
        logger.info(f"Started new run with ID: {run_id} for query: {query}")
        return run_id

    def finish_run(self, run_id: str, status_code: int) -> None:
        now = self._now_iso()
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                UPDATE tasks SET finished_at = ?, successful = ? WHERE run_id = ?
                """,
                (now, status_code, run_id),
            )

    def start_node(self, run_id: str, node: str) -> int:
        now = self._now_iso()
        with self._lock, self._connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO progress(run_id, node, created_at)
                VALUES (?, ?, ?)
                """,
                (run_id, node, now),
            )
            return int(cur.lastrowid)

    def finish_node(self, run_id: str, node: str, final_context: str, status_code: int) -> None:
        now = self._now_iso()
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                UPDATE progress
                SET finished_at = ?, final_context = ?, successful = ?
                WHERE run_id = ? AND node = ?
                """,
                (now, final_context, status_code, run_id, node),
            )

    def get_skill_history_meta(self, run_id: str, skill_name: str) -> dict:
        skill_node = f"skill.{skill_name}"
        with self._lock, self._connect() as conn:
            row = conn.execute(
                """
                SELECT id
                FROM progress_nodes
                WHERE run_id = ? AND node = ?
                ORDER BY id DESC
                LIMIT 1
                """,
                (run_id, skill_node),
            ).fetchone()

            cnt = conn.execute(
                """
                SELECT COUNT(*) AS c
                FROM progress_nodes
                WHERE run_id = ? AND node = ?
                """,
                (run_id, skill_node),
            ).fetchone()["c"]

        return {
            "has_history": cnt > 0,
            "count": int(cnt),
            "last_skill_node_id": int(row["id"]) if row else None,
        }

    def build_skill_prompt(self, run_id: str, root_query: str, skill_name: str) -> str:
        skill_node = f"skill.{skill_name}"
        meta = self.get_skill_history_meta(run_id, skill_name)

        global_budget = int(self.max_chars * 0.45)
        skill_budget = int(self.max_chars * 0.35)
        delta_budget = self.max_chars - global_budget - skill_budget

        with self._lock, self._connect() as conn:
            global_rows = conn.execute(
                """
                SELECT node, summary_text
                FROM progress_nodes
                WHERE run_id = ? AND node <> ?
                ORDER BY id DESC
                LIMIT 12
                """,
                (run_id, skill_node),
            ).fetchall()  # 当前问题下, 非当前skill的历史结果, 按时间倒序取最近的12条

            global_rows = list(reversed(global_rows))

            skill_rows = []
            delta_rows = []

            if meta["has_history"]:
                skill_rows = conn.execute(
                    """
                    SELECT node, summary_text
                    FROM progress_nodes
                    WHERE run_id = ? AND node = ?
                    ORDER BY id DESC
                    LIMIT 4
                    """,
                    (run_id, skill_node),
                ).fetchall()  # 当前问题下, 当前skill的历史结果, 按时间倒序取最近的4条
                skill_rows = list(reversed(skill_rows))

                delta_rows = conn.execute(
                    """
                    SELECT node, summary_text
                    FROM progress_nodes
                    WHERE run_id = ?
                      AND id > ?
                      AND node <> ?
                    ORDER BY id ASC
                    LIMIT 10
                    """,
                    (run_id, meta["last_skill_node_id"], skill_node),
                ).fetchall()  # 当前问题下, 当前skill上次执行之后的历史结果, 按时间正序取最近的10条

        global_text = self._format_rows(global_rows, global_budget)
        skill_text = self._format_rows(skill_rows, skill_budget)
        delta_text = self._format_rows(delta_rows, delta_budget)

        has_history_text = "是" if meta["has_history"] else "否"

        return (
            f"用户原始需求: {root_query}\n\n"
            f"当前调用技能: {skill_name}\n\n"
            f"当前技能是否有历史: {has_history_text}\n\n"
            f"当前总任务最近进展(摘要):\n{global_text}\n\n"
            f"当前技能历史结果(摘要):\n{skill_text}\n\n"
            f"自上次调用该技能后的新增进展(摘要):\n{delta_text}\n\n"
            "请基于以上信息推进任务。\n"
            "如果当前技能是首次调用，优先参考总任务最近进展。\n"
            "如果不是首次调用，不要重复已经完成的步骤。"
        )

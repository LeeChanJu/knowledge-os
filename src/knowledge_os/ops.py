import json
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from time import perf_counter
from uuid import uuid4


class OpsStore:
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init()

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.path)
        try:
            yield connection
            connection.commit()
        finally:
            connection.close()

    def _init(self) -> None:
        with self.connect() as db:
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS telemetry (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    operation TEXT NOT NULL,
                    status TEXT NOT NULL,
                    duration_ms REAL NOT NULL,
                    context_json TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS feedback (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    trace_id TEXT NOT NULL,
                    rating INTEGER,
                    comment TEXT,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS evaluations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    question TEXT NOT NULL,
                    expected_json TEXT NOT NULL,
                    actual_json TEXT,
                    score REAL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS audit_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    actor TEXT NOT NULL,
                    action TEXT NOT NULL,
                    target TEXT NOT NULL,
                    detail_json TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS retrieval_traces (
                    trace_id TEXT PRIMARY KEY,
                    query TEXT NOT NULL,
                    mode TEXT NOT NULL,
                    result_count INTEGER NOT NULL,
                    result_ids_json TEXT NOT NULL,
                    duration_ms REAL NOT NULL,
                    contract_version TEXT NOT NULL,
                    context_json TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS errors (
                    error_id TEXT PRIMARY KEY,
                    operation TEXT NOT NULL,
                    error_type TEXT NOT NULL,
                    message TEXT NOT NULL,
                    context_json TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                """
            )
            self._ensure_column(db, "feedback", "actor", "TEXT")
            self._ensure_column(db, "feedback", "workspace_id", "TEXT")
            self._ensure_column(db, "feedback", "access_fingerprint", "TEXT")
            self._ensure_column(db, "evaluations", "trace_id", "TEXT")
            self._ensure_column(db, "evaluations", "evaluator_version", "TEXT")
            self._ensure_column(db, "evaluations", "workspace_id", "TEXT")
            self._ensure_column(db, "evaluations", "access_fingerprint", "TEXT")
            self._backfill_feedback_access(db)
            self._backfill_evaluation_access(db)

    @staticmethod
    def _ensure_column(db: sqlite3.Connection, table: str, column: str, declaration: str) -> None:
        columns = {row[1] for row in db.execute(f"PRAGMA table_info({table})")}
        if column not in columns:
            db.execute(f"ALTER TABLE {table} ADD COLUMN {column} {declaration}")

    @staticmethod
    def _backfill_evaluation_access(db: sqlite3.Connection) -> None:
        rows = db.execute(
            """
            SELECT evaluations.id,retrieval_traces.context_json
            FROM evaluations
            JOIN retrieval_traces ON retrieval_traces.trace_id=evaluations.trace_id
            WHERE evaluations.workspace_id IS NULL
               OR evaluations.access_fingerprint IS NULL
            """
        ).fetchall()
        for evaluation_id, context_json in rows:
            context = json.loads(context_json)
            workspace_id = context.get("workspace_id")
            fingerprint = context.get("access_fingerprint")
            if workspace_id and fingerprint:
                db.execute(
                    """
                    UPDATE evaluations
                    SET workspace_id=?,access_fingerprint=?
                    WHERE id=?
                    """,
                    (workspace_id, fingerprint, evaluation_id),
                )

    @staticmethod
    def _backfill_feedback_access(db: sqlite3.Connection) -> None:
        rows = db.execute(
            """
            SELECT feedback.id,retrieval_traces.context_json
            FROM feedback
            JOIN retrieval_traces ON retrieval_traces.trace_id=feedback.trace_id
            WHERE feedback.workspace_id IS NULL
               OR feedback.access_fingerprint IS NULL
            """
        ).fetchall()
        for feedback_id, context_json in rows:
            context = json.loads(context_json)
            workspace_id = context.get("workspace_id")
            fingerprint = context.get("access_fingerprint")
            if workspace_id and fingerprint:
                db.execute(
                    """
                    UPDATE feedback
                    SET workspace_id=?,access_fingerprint=?
                    WHERE id=?
                    """,
                    (workspace_id, fingerprint, feedback_id),
                )

    def telemetry(self, operation: str, status: str, started: float, **context: object) -> None:
        with self.connect() as db:
            db.execute(
                "INSERT INTO telemetry(operation,status,duration_ms,context_json) VALUES(?,?,?,?)",
                (operation, status, (perf_counter() - started) * 1000, json.dumps(context)),
            )

    def audit(self, actor: str, action: str, target: str, **detail: object) -> None:
        with self.connect() as db:
            db.execute(
                "INSERT INTO audit_log(actor,action,target,detail_json) VALUES(?,?,?,?)",
                (actor, action, target, json.dumps(detail, ensure_ascii=False)),
            )

    def retrieval_trace(
        self,
        query: str,
        mode: str,
        started: float,
        result_ids: list[str],
        contract_version: str = "retrieval-v1",
        **context: object,
    ) -> str:
        trace_id = f"trace:{uuid4()}"
        with self.connect() as db:
            db.execute(
                """
                INSERT INTO retrieval_traces(
                    trace_id,query,mode,result_count,result_ids_json,duration_ms,
                    contract_version,context_json
                ) VALUES(?,?,?,?,?,?,?,?)
                """,
                (
                    trace_id,
                    query,
                    mode,
                    len(result_ids),
                    json.dumps(result_ids),
                    (perf_counter() - started) * 1000,
                    contract_version,
                    json.dumps(context, ensure_ascii=False),
                ),
            )
        return trace_id

    def get_trace(self, trace_id: str) -> dict | None:
        with self.connect() as db:
            db.row_factory = sqlite3.Row
            row = db.execute(
                "SELECT * FROM retrieval_traces WHERE trace_id=?", (trace_id,)
            ).fetchone()
        if row is None:
            return None
        result = dict(row)
        result["result_ids"] = json.loads(result.pop("result_ids_json"))
        result["context"] = json.loads(result.pop("context_json"))
        return result

    def get_trace_for_access(
        self, trace_id: str, workspace_id: str, fingerprint: str
    ) -> dict | None:
        trace = self.get_trace(trace_id)
        if trace is None:
            return None
        context = trace["context"]
        if (
            context.get("workspace_id") != workspace_id
            or context.get("access_fingerprint") != fingerprint
        ):
            return None
        return trace

    def record_feedback(
        self, trace_id: str, rating: int | None, comment: str | None, actor: str | None
    ) -> int:
        with self.connect() as db:
            row = db.execute(
                "SELECT context_json FROM retrieval_traces WHERE trace_id=?", (trace_id,)
            ).fetchone()
            if row is None:
                raise KeyError(trace_id)
            trace_context = json.loads(row[0])
            workspace_id = trace_context.get("workspace_id")
            fingerprint = trace_context.get("access_fingerprint")
            if not workspace_id or not fingerprint:
                raise ValueError("retrieval trace has no access provenance")
            cursor = db.execute(
                """
                INSERT INTO feedback(
                    trace_id,rating,comment,actor,workspace_id,access_fingerprint
                ) VALUES(?,?,?,?,?,?)
                """,
                (trace_id, rating, comment, actor, workspace_id, fingerprint),
            )
            return int(cursor.lastrowid)

    def record_evaluation(
        self,
        question: str,
        expected: object,
        actual: object | None,
        score: float | None,
        evaluator_version: str,
        trace_id: str | None = None,
        *,
        workspace_id: str | None = None,
        access_fingerprint: str | None = None,
    ) -> int:
        with self.connect() as db:
            if trace_id:
                row = db.execute(
                    "SELECT context_json FROM retrieval_traces WHERE trace_id=?", (trace_id,)
                ).fetchone()
                if row is None:
                    raise KeyError(trace_id)
                trace_context = json.loads(row[0])
                trace_workspace = trace_context.get("workspace_id")
                trace_fingerprint = trace_context.get("access_fingerprint")
                if not trace_workspace or not trace_fingerprint:
                    raise ValueError("retrieval trace has no access provenance")
                if workspace_id is not None and workspace_id != trace_workspace:
                    raise ValueError("evaluation workspace does not match retrieval trace")
                if access_fingerprint is not None and access_fingerprint != trace_fingerprint:
                    raise ValueError("evaluation access does not match retrieval trace")
                workspace_id = trace_workspace
                access_fingerprint = trace_fingerprint
            elif not workspace_id or not access_fingerprint:
                raise ValueError("unlinked evaluation requires workspace and access fingerprint")
            cursor = db.execute(
                """
                INSERT INTO evaluations(
                    question,expected_json,actual_json,score,trace_id,evaluator_version,
                    workspace_id,access_fingerprint
                ) VALUES(?,?,?,?,?,?,?,?)
                """,
                (
                    question,
                    json.dumps(expected, ensure_ascii=False),
                    json.dumps(actual, ensure_ascii=False) if actual is not None else None,
                    score,
                    trace_id,
                    evaluator_version,
                    workspace_id,
                    access_fingerprint,
                ),
            )
            return int(cursor.lastrowid)

    def error(
        self, operation: str, exc: Exception, *, safe_message: str | None = None, **context: object
    ) -> str:
        error_id = f"error:{uuid4()}"
        with self.connect() as db:
            db.execute(
                """
                INSERT INTO errors(error_id,operation,error_type,message,context_json)
                VALUES(?,?,?,?,?)
                """,
                (
                    error_id,
                    operation,
                    type(exc).__name__,
                    safe_message if safe_message is not None else str(exc),
                    json.dumps(context, ensure_ascii=False),
                ),
            )
        return error_id

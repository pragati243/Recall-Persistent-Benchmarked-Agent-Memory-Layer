import psycopg
from psycopg.rows import dict_row

from .config import settings

_SCHEMA = """
CREATE TABLE IF NOT EXISTS memory_audit (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL,
    entity_key TEXT NOT NULL,
    entity_name TEXT NOT NULL,
    relation TEXT NOT NULL,
    target_key TEXT NOT NULL,
    target_name TEXT NOT NULL,
    memory_id TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    superseded_at TIMESTAMPTZ,
    superseded_by_memory_id TEXT
);
"""


class AuditStore:
    """Append-only audit trail in Postgres — the record of what was asserted and
    when, kept separate from Neo4j (which only reflects current state)."""

    def __init__(self) -> None:
        self._dsn = settings.postgres_dsn
        self._schema_ready = False

    def _connect(self) -> psycopg.Connection:
        conn = psycopg.connect(self._dsn, row_factory=dict_row, autocommit=True)
        if not self._schema_ready:
            conn.execute(_SCHEMA)
            self._schema_ready = True
        return conn

    def find_active(self, user_id: str, entity_key: str, relation: str) -> list[dict]:
        with self._connect() as conn:
            return conn.execute(
                """SELECT * FROM memory_audit
                   WHERE user_id = %s AND entity_key = %s AND relation = %s AND superseded_at IS NULL""",
                (user_id, entity_key, relation),
            ).fetchall()

    def supersede(self, audit_id, memory_id: str) -> None:
        with self._connect() as conn:
            conn.execute(
                "UPDATE memory_audit SET superseded_at = now(), superseded_by_memory_id = %s WHERE id = %s",
                (memory_id, audit_id),
            )

    def record(
        self, user_id: str, entity_key: str, entity_name: str, relation: str,
        target_key: str, target_name: str, memory_id: str,
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                """INSERT INTO memory_audit
                   (user_id, entity_key, entity_name, relation, target_key, target_name, memory_id)
                   VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                (user_id, entity_key, entity_name, relation, target_key, target_name, memory_id),
            )

    def history(self, user_id: str, entity_key: str) -> list[dict]:
        with self._connect() as conn:
            return conn.execute(
                "SELECT * FROM memory_audit WHERE user_id = %s AND entity_key = %s ORDER BY created_at",
                (user_id, entity_key),
            ).fetchall()


audit_store = AuditStore()

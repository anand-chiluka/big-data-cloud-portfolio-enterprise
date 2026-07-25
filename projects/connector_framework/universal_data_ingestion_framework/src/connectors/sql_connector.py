"""
Structured SQL connector: extracts from traditional and cloud relational
databases (PostgreSQL, SQL Server, Oracle DB, Aurora, Azure SQL, Cloud SQL).

This is written against Python's built-in sqlite3 so it can be fully
exercised without any real database server or credentials, while the
extraction pattern (parameterized incremental query, cursor tracking)
is identical to what a psycopg2/pyodbc/cx_Oracle connector would do
against a real PostgreSQL, SQL Server, or Oracle instance. Swapping the
connection object is the only change needed to point this at a real
database.
"""

from __future__ import annotations

import sqlite3
from typing import Optional

from .base import BaseConnector, ExtractedRecord, ExtractionResult, SourceCategory


class SQLConnector(BaseConnector):
    """Incremental extraction from a relational source using a
    high-water-mark column (commonly `updated_at`), the standard pattern
    for pulling only rows that changed since the last successful run.
    """

    category = SourceCategory.STRUCTURED_SQL

    def __init__(self, connection, table_name: str, cursor_column: str = "updated_at",
                 primary_key: str = "id", connector_name: Optional[str] = None):
        self.connection = connection
        self.table_name = table_name
        self.cursor_column = cursor_column
        self.primary_key = primary_key
        self.name = connector_name or f"sql:{table_name}"
        self._cursor_value: Optional[str] = None

    def get_cursor(self) -> Optional[str]:
        return self._cursor_value

    def set_cursor(self, cursor: str) -> None:
        self._cursor_value = cursor

    def extract(self) -> ExtractionResult:
        cur = self.connection.cursor()

        if self._cursor_value:
            query = (
                f"SELECT * FROM {self.table_name} "
                f"WHERE {self.cursor_column} > ? ORDER BY {self.cursor_column} ASC"
            )
            cur.execute(query, (self._cursor_value,))
        else:
            query = f"SELECT * FROM {self.table_name} ORDER BY {self.cursor_column} ASC"
            cur.execute(query)

        columns = [desc[0] for desc in cur.description]
        rows = cur.fetchall()

        records = []
        for row in rows:
            row_dict = dict(zip(columns, row))
            records.append(ExtractedRecord(
                source_name=self.name,
                source_category=self.category,
                record_id=str(row_dict[self.primary_key]),
                payload=row_dict,
                content_type="structured",
            ))

        if rows:
            self._cursor_value = str(dict(zip(columns, rows[-1]))[self.cursor_column])

        return ExtractionResult(records=records, errors=[], source_name=self.name)


def build_demo_sqlite_source() -> sqlite3.Connection:
    """Builds an in-memory SQLite database standing in for a real
    PostgreSQL/SQL Server/Oracle source, so SQLConnector can be exercised
    without any real database server.
    """
    conn = sqlite3.connect(":memory:")
    conn.execute("""
        CREATE TABLE customers (
            id INTEGER PRIMARY KEY,
            name TEXT,
            country TEXT,
            updated_at TEXT
        )
    """)
    conn.executemany(
        "INSERT INTO customers (id, name, country, updated_at) VALUES (?, ?, ?, ?)",
        [
            (1, "Acme Corp", "US", "2026-01-01T00:00:00"),
            (2, "Globex", "GB", "2026-01-02T00:00:00"),
            (3, "Initech", "CA", "2026-01-03T00:00:00"),
        ],
    )
    conn.commit()
    return conn

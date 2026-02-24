"""SQLite FTS5 storage layer for catalog search (SPEC-2 Task 1.2).

Provides full-text search over data source metadata and knowledge entries
using SQLite's FTS5 extension with trigram tokenization.
"""

import logging
import sqlite3
from pathlib import Path
from sqlite3 import OperationalError

logger = logging.getLogger(__name__)

_CREATE_FTS_TABLE = (
    "CREATE VIRTUAL TABLE IF NOT EXISTS catalog_fts "
    "USING fts5(doc_type, source_id, title, content, tokenize='trigram')"
)

_DROP_FTS_TABLE = "DROP TABLE IF EXISTS catalog_fts"

_INSERT_ROW = (
    "INSERT INTO catalog_fts(doc_type, source_id, title, content) VALUES (?, ?, ?, ?)"
)

_SEARCH_QUERY = (
    "SELECT doc_type, source_id, title, "
    "snippet(catalog_fts, 3, '<b>', '</b>', '...', 32) as snippet, "
    "rank "
    "FROM catalog_fts WHERE catalog_fts MATCH ? "
    "ORDER BY rank LIMIT ?"
)

_DELETE_BY_SOURCE = "DELETE FROM catalog_fts WHERE source_id = ?"


def _open_connection(db_path: Path) -> sqlite3.Connection:
    """Open a SQLite connection with WAL mode and busy timeout."""
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    return conn


def _build_source_content(source: dict) -> str:
    """Build searchable content string from a source metadata dict."""
    parts = [source.get("description", "")]
    for col in source.get("columns", []):
        parts.append(col.get("name", ""))
        parts.append(col.get("description", ""))
    return " ".join(parts)


def build_index(
    db_path: Path,
    sources: list[dict],
    knowledge: list[dict],
) -> None:
    """Build (or rebuild) the FTS5 index from scratch.

    Drops any existing index and creates a new one populated with
    the given sources and knowledge entries.

    Args:
        db_path: Path to the SQLite database file.
        sources: List of source metadata dicts with keys:
            id, name, description, columns.
        knowledge: List of knowledge entry dicts with keys:
            source_id, title, content.
    """
    try:
        conn = sqlite3.connect(str(db_path))
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=5000")

        conn.execute(_DROP_FTS_TABLE)
        conn.execute(_CREATE_FTS_TABLE)

        rows: list[tuple[str, str, str, str]] = []
        for src in sources:
            content = _build_source_content(src)
            rows.append(("source", src["id"], src.get("name", ""), content))

        for entry in knowledge:
            rows.append(
                (
                    "knowledge",
                    entry.get("source_id", ""),
                    entry.get("title", ""),
                    entry.get("content", ""),
                )
            )

        if rows:
            conn.executemany(_INSERT_ROW, rows)

        conn.commit()
        conn.close()
    except OperationalError as exc:
        logger.warning("build_index failed: %s", exc)


def search_index(
    db_path: Path,
    query: str,
    limit: int = 20,
) -> list[dict]:
    """Search the FTS5 index and return ranked results.

    Args:
        db_path: Path to the SQLite database file.
        query: Search query string.
        limit: Maximum number of results to return.

    Returns:
        List of result dicts with keys:
        doc_type, source_id, title, snippet, rank.
        Empty list if no matches or on error.
    """
    if not query or not query.strip():
        return []

    if not db_path.exists():
        return []

    try:
        conn = _open_connection(db_path)
        sanitized = '"' + query.replace('"', '""') + '"'
        cursor = conn.execute(_SEARCH_QUERY, (sanitized, limit))
        results = [
            {
                "doc_type": row[0],
                "source_id": row[1],
                "title": row[2],
                "snippet": row[3],
                "rank": row[4],
            }
            for row in cursor.fetchall()
        ]
        conn.close()
        return results
    except OperationalError as exc:
        logger.warning("search_index failed: %s", exc)
        return []


def insert_document(
    db_path: Path,
    doc_type: str,
    source_id: str,
    title: str,
    content: str,
) -> None:
    """Insert a single document into the FTS5 index.

    Args:
        db_path: Path to the SQLite database file.
        doc_type: Document type ('source' or 'knowledge').
        source_id: Source identifier.
        title: Document title.
        content: Searchable content text.
    """
    try:
        conn = _open_connection(db_path)
        conn.execute(_INSERT_ROW, (doc_type, source_id, title, content))
        conn.commit()
        conn.close()
    except OperationalError as exc:
        logger.warning("insert_document failed: %s", exc)


def delete_source_documents(db_path: Path, source_id: str) -> None:
    """Delete all documents for a given source_id.

    Args:
        db_path: Path to the SQLite database file.
        source_id: Source identifier whose documents to remove.
    """
    try:
        conn = _open_connection(db_path)
        conn.execute(_DELETE_BY_SOURCE, (source_id,))
        conn.commit()
        conn.close()
    except OperationalError as exc:
        logger.warning("delete_source_documents failed: %s", exc)


def replace_source_documents(
    db_path: Path,
    source_id: str,
    rows: list[dict],
) -> None:
    """Atomically replace all documents for a source_id.

    Uses BEGIN IMMEDIATE to ensure the delete + insert is atomic.

    Args:
        db_path: Path to the SQLite database file.
        source_id: Source identifier whose documents to replace.
        rows: List of dicts with keys: doc_type, source_id, title, content.
    """
    try:
        conn = _open_connection(db_path)
        conn.execute("BEGIN IMMEDIATE")
        conn.execute(_DELETE_BY_SOURCE, (source_id,))
        for row in rows:
            conn.execute(
                _INSERT_ROW,
                (
                    row["doc_type"],
                    row["source_id"],
                    row["title"],
                    row["content"],
                ),
            )
        conn.execute("COMMIT")
        conn.close()
    except OperationalError as exc:
        logger.warning("replace_source_documents failed: %s", exc)

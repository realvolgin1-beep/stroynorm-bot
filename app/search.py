import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class SearchHit:
    document: str
    page: int | None
    section: str | None
    text: str
    score: float


def _query_terms(question: str) -> str:
    words = re.findall(r"[0-9A-Za-zА-Яа-яЁё.-]{3,}", question)
    return " OR ".join(f'"{word.replace(chr(34), "")}"' for word in words[:12])


def search(database_path: str, question: str, limit: int = 7) -> list[SearchHit]:
    path = Path(database_path)
    if not path.exists():
        return []
    query = _query_terms(question)
    if not query:
        return []
    with sqlite3.connect(path) as connection:
        rows = connection.execute(
            """
            SELECT document, page, section, text, bm25(chunks) AS rank
            FROM chunks
            WHERE chunks MATCH ?
            ORDER BY rank
            LIMIT ?
            """,
            (query, limit),
        ).fetchall()
    return [SearchHit(row[0], row[1], row[2], row[3], float(row[4])) for row in rows]

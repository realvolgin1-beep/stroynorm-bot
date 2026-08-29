import sqlite3
from dataclasses import dataclass
from pathlib import Path

from app.catalog import documents
from app.smart_search import analyze_query, fts_query, text_relevance


@dataclass(frozen=True)
class SearchHit:
    document: str
    page: int | None
    section: str | None
    text: str
    score: float
    source_url: str | None = None
    edition: str | None = None


def _query_terms(question: str) -> str:
    return fts_query(question)


def _catalog_metadata(document: str) -> tuple[str | None, str | None]:
    normalized = document.lower().replace("ё", "е")
    for item in documents():
        code = item["code"].lower().replace("ё", "е")
        compact_code = code.replace(" ", "").replace("-", "")
        compact_document = normalized.replace(" ", "").replace("-", "")
        if code in normalized or compact_code in compact_document:
            return item.get("official_url"), item.get("edition")
    return None, None


def search(database_path: str, question: str, limit: int = 7) -> list[SearchHit]:
    path = Path(database_path)
    if not path.exists():
        return []
    query = _query_terms(question)
    if not query:
        return []
    profile = analyze_query(question)
    try:
        with sqlite3.connect(path) as connection:
            columns = {row[1] for row in connection.execute("PRAGMA table_info(chunks)")}
            source_column = "source_url" if "source_url" in columns else "NULL"
            edition_column = "edition" if "edition" in columns else "NULL"
            rows = connection.execute(
                f"""
                SELECT document, page, section, text, bm25(chunks) AS rank,
                       {source_column}, {edition_column}
                FROM chunks
                WHERE chunks MATCH ?
                ORDER BY rank
                LIMIT ?
                """,
                (query, max(limit * 4, limit)),
            ).fetchall()
    except sqlite3.OperationalError:
        return []

    hits = []
    for row in rows:
        source_url, edition = row[5], row[6]
        if not source_url or not edition:
            catalog_url, catalog_edition = _catalog_metadata(row[0])
            source_url = source_url or catalog_url
            edition = edition or catalog_edition
        lexical_score = text_relevance(profile, f"{row[0]} {row[2] or ''} {row[3]}")
        hits.append(
            SearchHit(
                document=row[0],
                page=row[1],
                section=row[2],
                text=row[3],
                score=lexical_score - float(row[4]),
                source_url=source_url,
                edition=edition,
            )
        )
    hits.sort(key=lambda hit: hit.score, reverse=True)
    return hits[:limit]

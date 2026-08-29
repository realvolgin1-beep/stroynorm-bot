import sqlite3
from dataclasses import dataclass
from pathlib import Path

from app.catalog import documents, search_catalog
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
    kind: str = "clause"
    category: str | None = None
    status: str | None = None


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


def _search_database(database_path: str, question: str, limit: int) -> list[SearchHit]:
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


def _catalog_search_hits(question: str, limit: int) -> list[SearchHit]:
    hits = []
    for index, item in enumerate(search_catalog(question, limit=limit)):
        scope = item.get("scope") or item["title"]
        hits.append(
            SearchHit(
                document=f"{item['code']} «{item['title']}»",
                page=None,
                section="область применения",
                text=scope,
                score=float(item.get("_search_score", limit - index)),
                source_url=item.get("official_url"),
                edition=item.get("edition"),
                kind="catalog",
                category=item.get("category"),
                status=item.get("status"),
            )
        )
    return hits


def search(database_path: str, question: str, limit: int = 7) -> list[SearchHit]:
    """Search verified clauses first and document scopes second.

    Catalog scopes are bundled with the application, so broad construction
    routing works on an ephemeral free Render instance even when a separate
    SQLite corpus has not been mounted.  A catalog hit is explicitly marked and
    must never be formatted as a numerical requirement.
    """

    clause_hits = _search_database(database_path, question, limit)
    catalog_hits = _catalog_search_hits(question, limit)
    if not clause_hits:
        return catalog_hits[:limit]

    result = list(clause_hits)
    normalized_clause_documents = " ".join(hit.document.lower() for hit in clause_hits)
    for hit in catalog_hits:
        code = hit.document.split(" «", 1)[0].lower()
        if code in normalized_clause_documents:
            continue
        result.append(hit)
        if len(result) >= limit:
            break
    return result[:limit]

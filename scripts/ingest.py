import argparse
import re
import sqlite3
from pathlib import Path

from pypdf import PdfReader

from app.catalog import documents as catalog_documents


SECTION_PATTERN = re.compile(
    r"(?mi)^\s*("
    r"(?:(?:пункт|п\.)\s*)?(?:\d+\.)+\d+"
    r"|(?:статья|раздел|таблица|приложение)\s+[0-9а-яa-zivx.-]+"
    r")\s+"
)


def chunks(text: str, size: int = 1800, overlap: int = 250):
    cleaned = re.sub(r"[ \t]+", " ", text)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned).strip()
    start = 0
    while start < len(cleaned):
        end = min(len(cleaned), start + size)
        if end < len(cleaned):
            boundary = cleaned.rfind("\n", start + size // 2, end)
            if boundary > start:
                end = boundary
        yield cleaned[start:end].strip()
        if end >= len(cleaned):
            break
        start = max(start + 1, end - overlap)


def section_for(text: str) -> str | None:
    matches = list(SECTION_PATTERN.finditer(text[:500]))
    return matches[-1].group(1) if matches else None


def read_document(path: Path):
    if path.suffix.lower() == ".pdf":
        reader = PdfReader(path)
        for number, page in enumerate(reader.pages, 1):
            yield number, page.extract_text() or ""
    elif path.suffix.lower() in {".txt", ".md"}:
        yield None, path.read_text(encoding="utf-8", errors="ignore")


def metadata_for(path: Path) -> tuple[str | None, str | None]:
    compact_name = re.sub(r"[^0-9a-zа-я]", "", path.stem.lower().replace("ё", "е"))
    for document in catalog_documents():
        compact_code = re.sub(r"[^0-9a-zа-я]", "", document["code"].lower().replace("ё", "е"))
        if compact_code and compact_code in compact_name:
            return document.get("official_url"), document.get("edition")
    return None, None


def ingest(source: Path, database: Path) -> tuple[int, int]:
    database.parent.mkdir(parents=True, exist_ok=True)
    documents = [p for p in source.rglob("*") if p.suffix.lower() in {".pdf", ".txt", ".md"}]
    inserted = 0
    with sqlite3.connect(database) as connection:
        connection.execute("DROP TABLE IF EXISTS chunks")
        connection.execute(
            "CREATE VIRTUAL TABLE chunks USING fts5("
            "document, page UNINDEXED, section UNINDEXED, text, "
            "source_url UNINDEXED, edition UNINDEXED, tokenize='unicode61')"
        )
        for path in documents:
            source_url, edition = metadata_for(path)
            for page, text in read_document(path):
                for fragment in chunks(text):
                    if len(fragment) < 80:
                        continue
                    connection.execute(
                        "INSERT INTO chunks(document, page, section, text, source_url, edition) "
                        "VALUES (?, ?, ?, ?, ?, ?)",
                        (path.stem, page, section_for(fragment), fragment, source_url, edition),
                    )
                    inserted += 1
        connection.commit()
    return len(documents), inserted


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("--database", type=Path, default=Path("data/stroynorm.db"))
    args = parser.parse_args()
    count, inserted = ingest(args.source, args.database)
    print(f"Обработано документов: {count}; фрагментов: {inserted}")


if __name__ == "__main__":
    main()

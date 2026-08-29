import json
from functools import lru_cache
from pathlib import Path

from app.smart_search import normalize, stem_word, tokenize


REQUIREMENTS_PATH = Path(__file__).resolve().parent.parent / "data" / "requirements.json"


@lru_cache
def requirements() -> list[dict]:
    return json.loads(REQUIREMENTS_PATH.read_text(encoding="utf-8"))


def requirement_values_count() -> int:
    return sum(len(item.get("parameters", [])) for item in requirements())


def _stems(text: str) -> tuple[str, ...]:
    return tuple(dict.fromkeys(stem_word(token) for token in tokenize(text)))


def _matches_term(query_stems: tuple[str, ...], term: str) -> bool:
    term_stems = _stems(term)
    if not term_stems:
        return False
    for expected in term_stems:
        if not any(
            actual == expected
            or (
                len(actual) >= 4
                and len(expected) >= 4
                and (actual.startswith(expected) or expected.startswith(actual))
            )
            for actual in query_stems
        ):
            return False
    return True


def _matches_record(query: str, record: dict) -> bool:
    query_stems = _stems(query)
    normalized_query = normalize(query)
    if any(_matches_term(query_stems, term) for term in record.get("exclude", [])):
        return False
    for group in record.get("match_groups", []):
        if not any(
            normalize(term) in normalized_query or _matches_term(query_stems, term)
            for term in group
        ):
            return False
    return True


def _selected_parameters(query: str, record: dict) -> list[dict]:
    query_stems = _stems(query)
    selected = [
        parameter
        for parameter in record.get("parameters", [])
        if parameter.get("keywords")
        and any(_matches_term(query_stems, keyword) for keyword in parameter["keywords"])
    ]
    return selected or record.get("parameters", [])


def _format_record(query: str, record: dict) -> str:
    lines = [f"📏 {record['title']}", "", record["intro"]]
    for parameter in _selected_parameters(query, record):
        lines.append(f"• {parameter['label']}: {parameter['value']}")

    if record.get("condition"):
        lines.extend(["", f"Условия: {record['condition']}"])
    if record.get("control"):
        lines.append(f"Контроль: {record['control']}")

    lines.extend(
        [
            "",
            f"Норматив: {record['document']}",
            f"Место: {record['location']}",
            f"Редакция: {record['edition']}; проверено {record['checked_at']}",
            f"Официальная карточка: {record['official_url']}",
        ]
    )

    for related in record.get("related_documents", []):
        lines.extend(
            [
                "",
                f"Связанный документ: {related['document']}, {related['location']}",
                f"Пояснение: {related['note']}",
                f"Официальная карточка: {related['official_url']}",
            ]
        )

    if record.get("note"):
        lines.extend(["", f"Важно: {record['note']}"])
    lines.extend(["", "Перед применением проверьте актуальность официальной редакции документа."])
    return "\n".join(lines)[:4090]


def answer_requirement(query: str) -> str | None:
    for record in requirements():
        if _matches_record(query, record):
            return _format_record(query, record)
    return None

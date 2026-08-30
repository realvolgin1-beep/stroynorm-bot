import json
from datetime import date
from difflib import SequenceMatcher
from functools import lru_cache
from pathlib import Path

from app.smart_search import normalize, stem_word, tokenize


REQUIREMENTS_PATH = Path(__file__).resolve().parent.parent / "data" / "requirements.json"


@lru_cache
def requirements() -> list[dict]:
    return json.loads(REQUIREMENTS_PATH.read_text(encoding="utf-8"))


def requirement_values_count(on_date: date | None = None) -> int:
    return sum(
        len(item.get("parameters", []))
        for item in requirements()
        if _is_effective(item, on_date)
    )


def _stems(text: str) -> tuple[str, ...]:
    return tuple(dict.fromkeys(stem_word(token) for token in tokenize(text)))


def _same_stem(actual: str, expected: str) -> bool:
    if actual == expected:
        return True
    short_actual = actual.rstrip("ьйияыа")
    short_expected = expected.rstrip("ьйияыа")
    if len(short_actual) >= 2 and short_actual == short_expected:
        return True
    if len(actual) < 4 or len(expected) < 4:
        return False
    if actual.startswith(expected) or expected.startswith(actual):
        return True
    return (
        len(actual) >= 5
        and len(expected) >= 5
        and actual[:4] == expected[:4]
        and abs(len(actual) - len(expected)) <= 3
        and SequenceMatcher(None, actual, expected).ratio() >= 0.82
    )


def _matches_term(query_stems: tuple[str, ...], term: str) -> bool:
    term_stems = _stems(term)
    if not term_stems:
        return False
    for expected in term_stems:
        if not any(_same_stem(actual, expected) for actual in query_stems):
            return False
    return True


def _is_effective(record: dict, on_date: date | None = None) -> bool:
    current = on_date or date.today()
    effective_from = record.get("effective_from")
    effective_until = record.get("effective_until")
    if effective_from and current < date.fromisoformat(effective_from):
        return False
    if effective_until and current > date.fromisoformat(effective_until):
        return False
    return True


def _matches_record(query: str, record: dict, on_date: date | None = None) -> bool:
    if not _is_effective(record, on_date):
        return False
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
    scored = []
    for parameter in record.get("parameters", []):
        if any(
            _matches_term(query_stems, keyword)
            for keyword in parameter.get("exclude_keywords", [])
        ):
            continue
        score = sum(
            1
            for keyword in parameter.get("keywords", [])
            if _matches_term(query_stems, keyword)
        )
        if score:
            scored.append((score, parameter))
    if not scored:
        return record.get("parameters", [])
    best_score = max(score for score, _ in scored)
    return [parameter for score, parameter in scored if score == best_score]


def _format_record(query: str, record: dict) -> str:
    selected_parameters = _selected_parameters(query, record)
    lines = []
    if len(selected_parameters) == 1:
        lines.extend([f"✅ Ответ: {selected_parameters[0]['value']}", ""])
    lines.extend([f"📏 {record['title']}", "", record["intro"]])
    for parameter in selected_parameters:
        line = f"• {parameter['label']}: {parameter['value']}"
        if parameter.get("location"):
            line += f" [{parameter['location']}]"
        lines.append(line)

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
    if record.get("future_change"):
        lines.extend(["", f"Изменение по дате: {record['future_change']}"])
    lines.extend(["", "Перед применением проверьте актуальность официальной редакции документа."])
    return "\n".join(lines)[:4090]


def answer_requirement(query: str, on_date: date | None = None) -> str | None:
    for record in requirements():
        if _matches_record(query, record, on_date):
            return _format_record(query, record)
    return None

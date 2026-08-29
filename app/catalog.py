import json
import re
from functools import lru_cache
from pathlib import Path


CATALOG_PATH = Path(__file__).resolve().parent.parent / "data" / "catalog.json"


@lru_cache
def documents() -> list[dict[str, str]]:
    return json.loads(CATALOG_PATH.read_text(encoding="utf-8"))


def catalog_summary(category: str | None = None) -> str:
    names = {
        "roads": "Автомобильные дороги",
        "bridges": "Мосты и трубы",
        "traffic": "Знаки и организация движения",
        "acceptance": "Контроль и приёмка",
        "maintenance": "Эксплуатация и содержание",
        "rosavtodor": "Минтранс и Росавтодор",
        "measurements": "Измерения и допустимые отклонения",
        "pavement": "Дорожные одежды и покрытия",
    }
    selected = [doc for doc in documents() if not category or doc["category"] == category]
    lines = [f"📚 {names.get(category, 'Реестр нормативных документов')} — {len(selected)} документов"]
    for doc in selected:
        scope = f"\nПрименение: {doc['scope']}" if doc.get("scope") else ""
        lines.append(f"\n• {doc['code']}\n{doc['title']}\nСтатус: {doc['status']}; {doc['edition']}{scope}")
    return "\n".join(lines)


def search_catalog(query: str, limit: int = 8) -> list[dict[str, str]]:
    normalized = query.lower().replace("ё", "е")
    terms = re.findall(r"[0-9a-zа-я.-]{2,}", normalized)
    aliases = {
        "мост": ["мост", "труб", "пролет", "опор", "сооружен"],
        "пролет": ["мост", "труб", "пролет", "опор", "сооружен"],
        "опор": ["мост", "труб", "пролет", "опор", "сооружен"],
        "усто": ["мост", "труб", "пролет", "опор", "сооружен"],
        "балк": ["мост", "пролет", "конструкц", "сооружен"],
        "ферм": ["мост", "пролет", "конструкц", "сооружен"],
        "ригел": ["мост", "опор", "конструкц", "сооружен"],
        "деформацион": ["мост", "пролет", "конструкц", "сооружен"],
        "дорог": ["дорог", "покрыт", "одежд", "полотн"],
        "знак": ["знак", "движен", "размет", "светофор"],
        "допуск": ["отклон", "геометр", "контрол", "измерен", "приемк"],
        "асфальт": ["асфальт", "покрыт", "смес"],
    }
    expanded = list(terms)
    for term in terms:
        for key, values in aliases.items():
            if term.startswith(key):
                expanded.extend(values)
    expanded = list(dict.fromkeys(expanded))

    has_document_number = any(re.search(r"\d{4,}", term) for term in terms)
    bridge_query = any(
        term.startswith(("мост", "пролет", "опор", "усто", "балк", "ферм", "ригел", "деформацион"))
        for term in terms
    )
    topic_boosts = {}
    if bridge_query and not has_document_number:
        topic_boosts = {
            "СП 35.13330.2011": 8,
            "ГОСТ 33384-2015": 7,
            "ГОСТ Р 59618-2021": 4,
            "СП 79.13330.2012": 3,
        }

    scored = []
    for doc in documents():
        haystack = " ".join(str(value) for value in doc.values()).lower().replace("ё", "е")
        score = sum(3 if term in doc["code"].lower() else 1 for term in expanded if term in haystack)
        score += topic_boosts.get(doc["code"], 0)
        if score:
            scored.append((score, doc))
    scored.sort(key=lambda item: (-item[0], item[1]["code"]))
    return [doc for _, doc in scored[:limit]]


def format_catalog_hits(hits: list[dict[str, str]]) -> str:
    lines = ["Нашёл подходящие нормативные документы:"]
    for doc in hits:
        lines.append(f"\n• {doc['code']} — {doc['title']}\nСтатус: {doc['status']}")
        if doc.get("scope"):
            lines.append(f"Применение: {doc['scope']}")
        lines.append(f"Источник: {doc['official_url']}")
    lines.append("\nУточните нужную работу или параметр: установка знака, ровность, уклон, сцепление, опора, пролетное строение, приемка и т. п.")
    return "\n".join(lines)

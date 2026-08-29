import json
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

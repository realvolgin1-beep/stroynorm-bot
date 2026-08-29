import json
import re
from collections import Counter
from functools import lru_cache
from pathlib import Path
from urllib.parse import quote_plus

from app.document_topics import DOCUMENT_SEARCH_TERMS
from app.smart_search import analyze_query, normalize, stem_word, text_relevance, tokenize


CATALOG_PATH = Path(__file__).resolve().parent.parent / "data" / "catalog.json"

CATEGORY_NAMES = {
    "roads": "Автомобильные дороги",
    "bridges": "Мосты и трубы",
    "traffic": "Знаки и организация движения",
    "acceptance": "Контроль и приёмка",
    "maintenance": "Эксплуатация и содержание",
    "rosavtodor": "Минтранс и Росавтодор",
    "measurements": "Измерения и допустимые отклонения",
    "pavement": "Дорожные одежды и покрытия",
    "organization": "Организация строительства",
    "structures": "Строительные конструкции и материалы",
    "geotechnics": "Основания, фундаменты и земляные работы",
    "fire": "Пожарная безопасность",
    "buildings": "Жилые, общественные и производственные здания",
    "engineering": "Инженерные системы",
    "finishes": "Кровли, изоляция, отделка и защита",
    "documentation": "Проектная и рабочая документация",
    "survey": "Изыскания, геодезия и обследования",
    "accessibility": "Доступность для МГН",
    "physics": "Строительная физика и климат",
    "urban": "Градостроительство и планировка",
}

DOCUMENT_PRIORITIES = {
    "bridges": ("СП 35.13330.2011", "ГОСТ 33384-2015", "СП 46.13330.2012", "ГОСТ Р 59618-2021", "СП 79.13330.2012"),
    "roads": ("СП 78.13330.2012", "СП 34.13330.2021"),
    "traffic": ("ГОСТ Р 52289-2019", "ГОСТ 32758-2014", "ГОСТ Р 52290-2004"),
    "measurements": ("ГОСТ Р 59120-2021", "ГОСТ Р 58945-2020", "ГОСТ 33383-2015", "ГОСТ Р 56925-2016"),
    "pavement": ("ГОСТ Р 59120-2021", "ГОСТ Р 71404-2024", "ГОСТ Р 70364-2022"),
    "organization": ("СП 48.13330.2019", "СП 70.13330.2012", "СП 68.13330.2017"),
    "structures": ("СП 20.13330.2016", "ГОСТ 27751-2014", "СП 63.13330.2018", "СП 16.13330.2017"),
    "geotechnics": ("СП 22.13330.2016", "СП 24.13330.2021", "СП 45.13330.2017"),
    "fire": ("СП 1.13130.2020", "СП 2.13130.2020", "СП 4.13130.2013", "СП 8.13130.2020"),
    "engineering": ("СП 60.13330.2020", "СП 73.13330.2016", "СП 30.13330.2020"),
    "documentation": ("ГОСТ Р 21.101-2026", "ГОСТ 21.501-2018"),
    "survey": ("ГОСТ 31937-2024", "СП 47.13330.2016", "СП 126.13330.2017"),
    "accessibility": ("СП 59.13330.2020",),
    "physics": ("СП 50.13330.2024", "СП 131.13330.2025", "СП 52.13330.2016", "СП 51.13330.2011"),
    "urban": ("СП 42.13330.2026",),
}


@lru_cache
def documents() -> list[dict]:
    return json.loads(CATALOG_PATH.read_text(encoding="utf-8"))


def catalog_summary(category: str | None = None) -> str:
    selected = [doc for doc in documents() if not category or doc["category"] == category]
    lines = [f"📚 {CATEGORY_NAMES.get(category, 'Реестр нормативных документов')} — {len(selected)} документов"]
    for doc in selected:
        scope = f"\nПрименение: {doc['scope']}" if doc.get("scope") else ""
        lines.append(f"\n• {doc['code']}\n{doc['title']}\nСтатус: {doc['status']}; {doc['edition']}{scope}")
    return "\n".join(lines)


def catalog_overview() -> str:
    counts = Counter(doc["category"] for doc in documents())
    lines = [f"📚 В проверенном реестре: {len(documents())} документов."]
    for category, title in CATEGORY_NAMES.items():
        if counts[category]:
            lines.append(f"• {title}: {counts[category]}")
    lines.append("\nНапишите тему или обозначение документа. Бот подберёт карточки и официальные ссылки.")
    return "\n".join(lines)


def catalog_scope_count() -> int:
    return sum(bool(document.get("scope")) for document in documents())


def search_catalog(query: str, limit: int = 8) -> list[dict]:
    profile = analyze_query(query)
    normalized_query = normalize(query)
    compact_query = re.sub(r"[^0-9a-zа-яё]", "", normalize(query))
    scored = []
    for doc in documents():
        search_terms = DOCUMENT_SEARCH_TERMS.get(doc["code"], ())
        haystack = " ".join(
            str(doc.get(field, ""))
            for field in ("code", "title", "scope", "category")
        )
        if search_terms:
            haystack += " " + " ".join(search_terms)
        compact_code = re.sub(r"[^0-9a-zа-яё]", "", normalize(doc["code"]))
        exact_compact_code = len(compact_query) >= 4 and compact_query in compact_code
        if not exact_compact_code and not profile.categories and len(profile.stems) > 1:
            document_stems = {stem_word(token) for token in tokenize(haystack)}
            matched_stems = sum(
                1
                for query_stem in profile.stems
                if any(
                    query_stem == document_stem
                    or (
                        len(query_stem) >= 4
                        and len(document_stem) >= 4
                        and (query_stem.startswith(document_stem) or document_stem.startswith(query_stem))
                    )
                    for document_stem in document_stems
                )
            )
            if matched_stems <= len(profile.stems) // 2:
                continue
        score = text_relevance(profile, haystack)
        normalized_code = normalize(doc["code"])
        score += sum(8.0 for token in profile.tokens if len(token) >= 2 and token in normalized_code)
        if exact_compact_code:
            score += 16.0
        if doc["category"] in profile.categories:
            score += 2.4

        topic_scores = []
        for term in search_terms:
            normalized_term = normalize(term)
            term_stems = tuple(dict.fromkeys(stem_word(token) for token in tokenize(term)))
            matching_stems = sum(
                1
                for expected in term_stems
                if any(
                    expected == actual
                    or (
                        len(expected) >= 4
                        and len(actual) >= 4
                        and (expected.startswith(actual) or actual.startswith(expected))
                    )
                    for actual in profile.stems
                )
            )
            if normalized_term in normalized_query:
                topic_scores.append(12.0 + len(term_stems))
            elif term_stems and matching_stems == len(term_stems):
                topic_scores.append(8.0 + matching_stems)
            elif matching_stems >= 2:
                topic_scores.append(3.0 + matching_stems)
        if topic_scores:
            score += max(topic_scores) + min(4.0, max(0, len(topic_scores) - 1) * 0.6)

        if not profile.has_document_number:
            for category in profile.categories:
                priorities = DOCUMENT_PRIORITIES.get(category, ())
                if doc["code"] in priorities:
                    score += 1.4 / (priorities.index(doc["code"]) + 1)
        if score >= 0.75:
            scored.append((score, doc))
    scored.sort(key=lambda item: (-item[0], item[1]["code"]))
    return [{**doc, "_search_score": score} for score, doc in scored[:limit]]


def format_catalog_hits(hits: list[dict]) -> str:
    lines = ["🧠 Бесплатный гибридный поиск нашёл подходящие документы:"]
    for doc in hits:
        lines.append(f"\n• {doc['code']} — {doc['title']}\nСтатус: {doc['status']}")
        if doc.get("scope"):
            lines.append(f"Применение: {doc['scope']}")
        lines.append(f"Официальная карточка: {doc['official_url']}")
    lines.append(
        "\nРекомендация: уточните вид работ, конструктивный элемент и параметр. "
        "Точные значения и пункты бот показывает только из загруженного официального текста."
    )
    return "\n".join(lines)


def format_no_results(query: str) -> str:
    gost_search = f"https://protect.gost.ru/?search={quote_plus(query)}"
    sp_search = f"https://protect.gost.ru/sp/?search={quote_plus(query)}"
    return (
        "В локальном реестре нет надёжного совпадения. Проверьте обозначение в официальном фонде:\n"
        f"• ГОСТ/ГОСТ Р: {gost_search}\n"
        f"• Своды правил: {sp_search}\n\n"
        "Добавьте объект, вид работ и нужный параметр."
    )


def catalog_sources() -> str:
    return (
        "🔗 Основные источники базы:\n\n"
        "• Федеральный информационный фонд стандартов Росстандарта:\nhttps://protect.gost.ru/\n\n"
        "• Документы Минстроя России:\nhttps://minstroyrf.gov.ru/docs/\n\n"
        "• Официальное опубликование правовых актов:\nhttps://publication.pravo.gov.ru/\n\n"
        "• ОДМ Росавтодора:\n"
        "https://rosavtodor.gov.ru/about/upravlenie-fda/upravlenie-nauchno-tekhnicheskikh-issledovaniy--i-informatsionnykh-tekhnologiy/tehnicheskoe-regulirovanie/otraslevye-dorozhnye-metodicheskie-dokumenty\n\n"
        "Перед применением проверяйте статус, изменения и дату введения документа."
    )

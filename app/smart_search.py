import re
from dataclasses import dataclass
from difflib import SequenceMatcher


WORD_PATTERN = re.compile(r"[0-9a-zа-яё.-]{2,}", re.IGNORECASE)

STOP_WORDS = {
    "без",
    "быть",
    "где",
    "для",
    "есть",
    "как",
    "какая",
    "какие",
    "какой",
    "можно",
    "надо",
    "нужно",
    "или",
    "при",
    "про",
    "что",
    "это",
}

RUSSIAN_SUFFIXES = (
    "ическими",
    "ического",
    "ическая",
    "ические",
    "ический",
    "ования",
    "ениями",
    "ениях",
    "ациями",
    "ациях",
    "ованный",
    "ованная",
    "ованные",
    "ованного",
    "ительный",
    "ительная",
    "ительные",
    "ствами",
    "ствах",
    "ения",
    "ением",
    "ация",
    "ации",
    "ацией",
    "ового",
    "евого",
    "ами",
    "ями",
    "ах",
    "ях",
    "ого",
    "его",
    "ому",
    "ему",
    "ыми",
    "ими",
    "ый",
    "ий",
    "ой",
    "ая",
    "яя",
    "ое",
    "ее",
    "ые",
    "ие",
    "ом",
    "ем",
    "ам",
    "ям",
    "ов",
    "ев",
    "ией",
    "иям",
    "иях",
    "ия",
    "ии",
    "ией",
    "ию",
    "ие",
    "ы",
    "и",
    "а",
    "я",
    "у",
    "ю",
    "е",
    "о",
)

TOPIC_MARKERS = {
    "bridges": ("мост", "путепровод", "эстакад", "пролет", "опор", "усто", "балк", "ферм", "ригел", "деформацион"),
    "roads": ("дорог", "трасс", "обочин", "насып", "выемк", "кювет", "откос", "водоотвод"),
    "traffic": ("знак", "размет", "светофор", "огражден", "одд", "тсодд"),
    "measurements": ("допуск", "отклон", "измер", "ровност", "уклон", "сцеплен", "геометр", "колейн"),
    "acceptance": ("приемк", "контрол", "исполнительн", "лаборатор", "отбор", "проб"),
    "pavement": ("асфальт", "покрыт", "щебен", "цементобетон", "дорожной одежд", "уплотнен"),
    "maintenance": ("дефект", "выбоин", "трещин", "содержан", "эксплуатац", "диагност"),
    "rosavtodor": ("росавтодор", "одм", "минтранс", "распоряжен"),
    "organization": ("организац", "стройконтрол", "ппр", "пос", "журнал работ"),
    "structures": (
        "бетон",
        "железобетон",
        "арматур",
        "стал",
        "металлоконструк",
        "кладк",
        "кирпич",
        "каменн",
        "деревян",
        "монолит",
        "сварк",
        "несущ",
        "нагруз",
    ),
    "geotechnics": ("фундамент", "основан", "грунт", "свай", "землян", "котлован", "геолог"),
    "fire": ("пожар", "эвакуац", "огнестой", "противопожар", "дымоудал"),
    "buildings": ("жил", "обществен", "производствен", "помещен", "здан"),
    "engineering": ("вентиляц", "отоплен", "водоснаб", "канализац", "электро", "газ", "котельн"),
    "finishes": ("кровл", "изоляц", "отделоч", "пол", "фасад", "корроз"),
    "documentation": ("проектн", "рабочая документац", "чертеж", "спдс", "исполнительн"),
    "survey": ("изыскан", "обследован", "мониторинг", "техническое состояние", "геодез"),
    "accessibility": ("мгн", "маломобил", "доступност", "пандус"),
    "physics": ("теплов", "освещен", "шум", "климат", "энергоэффект"),
}

TOPIC_EXPANSIONS = {
    "bridges": ("мост", "пролет", "опор", "сооружен"),
    "roads": ("дорог", "полотн", "обочин", "покрыт"),
    "traffic": ("знак", "движен", "размет", "светофор"),
    "measurements": ("отклон", "геометр", "контрол", "измерен"),
    "acceptance": ("приемк", "контрол", "качеств", "исполнительн"),
    "pavement": ("асфальт", "покрыт", "одежд", "уплотнен"),
    "maintenance": ("дефект", "содержан", "эксплуатац", "диагност"),
    "rosavtodor": ("росавтодор", "одм", "минтранс"),
    "organization": ("организац", "строительств", "контрол", "приемк"),
    "structures": ("конструкц", "несущ", "прочност", "нагруз"),
    "geotechnics": ("фундамент", "основан", "грунт", "свай"),
    "fire": ("пожар", "эвакуац", "огнестой", "противопожар"),
    "buildings": ("здан", "помещен", "проектирован"),
    "engineering": ("инженерн", "систем", "сет", "монтаж"),
    "finishes": ("изоляц", "отделк", "покрыт", "защит"),
    "documentation": ("проектн", "рабоч", "документац", "чертеж"),
    "survey": ("изыскан", "обследован", "мониторинг", "геодез"),
    "accessibility": ("доступност", "мгн", "пандус"),
    "physics": ("теплов", "освещен", "шум", "климат"),
}


@dataclass(frozen=True)
class QueryProfile:
    tokens: tuple[str, ...]
    stems: tuple[str, ...]
    expanded: tuple[str, ...]
    categories: tuple[str, ...]
    has_document_number: bool


def normalize(text: str) -> str:
    return text.lower().replace("ё", "е")


def tokenize(text: str) -> list[str]:
    return [normalize(word) for word in WORD_PATTERN.findall(text)]


def stem_word(word: str) -> str:
    normalized = normalize(word)
    if not normalized.isalpha() or len(normalized) < 5:
        return normalized
    for suffix in RUSSIAN_SUFFIXES:
        if normalized.endswith(suffix) and len(normalized) - len(suffix) >= 4:
            return normalized[: -len(suffix)]
    return normalized


def _close_word(word: str, marker: str) -> bool:
    if len(word) < 4 or len(marker) < 4:
        return word == marker
    if word.startswith(marker) or marker.startswith(word):
        return True
    if word[:4] != marker[:4] or abs(len(word) - len(marker)) > 3:
        return False
    return SequenceMatcher(None, word, marker).ratio() >= 0.78


def analyze_query(text: str) -> QueryProfile:
    tokens = tuple(dict.fromkeys(token for token in tokenize(text) if token not in STOP_WORDS))
    stems = tuple(dict.fromkeys(stem_word(token) for token in tokens))
    categories = []
    normalized_text = normalize(text)
    for category, markers in TOPIC_MARKERS.items():
        matched = any(" " in marker and marker in normalized_text for marker in markers)
        if not matched:
            matched = any(_close_word(stem, marker) for stem in stems for marker in markers if " " not in marker)
        if matched:
            categories.append(category)
    expanded = list(stems)
    for category in categories:
        expanded.extend(TOPIC_EXPANSIONS[category])
    return QueryProfile(
        tokens=tokens,
        stems=stems,
        expanded=tuple(dict.fromkeys(expanded)),
        categories=tuple(categories),
        has_document_number=any(re.search(r"\d{4,}", token) for token in tokens),
    )


def text_relevance(profile: QueryProfile, text: str) -> float:
    normalized_text = normalize(text)
    document_stems = tuple(dict.fromkeys(stem_word(token) for token in tokenize(text)))
    score = 0.0
    for token in profile.tokens:
        if len(token) >= 3 and token in normalized_text:
            score += 3.0
    for term in profile.expanded:
        if len(term) >= 4 and term in normalized_text:
            score += 1.0
    for query_stem in profile.stems:
        if len(query_stem) < 4 or not query_stem.isalpha():
            continue
        if query_stem in document_stems:
            score += 1.0
            continue
        candidates = (
            document_stem
            for document_stem in document_stems
            if len(document_stem) >= 4
            and document_stem[0] == query_stem[0]
            and abs(len(document_stem) - len(query_stem)) <= 3
        )
        best = max((SequenceMatcher(None, query_stem, candidate).ratio() for candidate in candidates), default=0.0)
        if best >= 0.9:
            score += 0.8
        elif best >= 0.78:
            score += 0.35
    return score


def fts_query(text: str, limit: int = 28) -> str:
    profile = analyze_query(text)
    pieces = []
    for token in profile.tokens:
        if len(token) >= 3:
            pieces.append(f'"{token}"')
        stem = stem_word(token)
        if stem.isalpha() and len(stem) >= 4:
            pieces.append(f'"{stem}"*')
    for term in profile.expanded:
        if term.isalpha() and len(term) >= 4:
            pieces.append(f'"{term}"*')
    return " OR ".join(dict.fromkeys(pieces[:limit]))

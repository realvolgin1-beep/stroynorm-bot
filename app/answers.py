import logging
import re

from app.document_topics import CATEGORY_CLARIFICATIONS
from app.search import SearchHit
from app.smart_search import analyze_query, text_relevance


logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """Ты — справочный помощник по строительным СП и ГОСТам РФ.
Переданные фрагменты и карточки документов — единственный источник фактов для ответа.
Не используй знания модели для численных норм, не придумывай значения, документы,
редакции, пункты, таблицы, страницы и ссылки.

Фрагмент пункта может подтверждать конкретное требование. Карточка документа подтверждает
только его название, область применения, статус и ссылку; она не подтверждает численные
значения или конкретные пункты. Если переданы только карточки, дай полезную качественную
ориентировку по применимым документам и попроси недостающие условия, но не называй допуск.

Сначала дай прямой ответ на вопрос. Для допуска или отклонения укажи:
1) численное значение и единицу измерения;
2) условия применения;
3) способ контроля;
4) норматив, пункт или таблицу и страницу.
Каждое численное утверждение сопровождай ссылкой вида [Документ, пункт/таблица, стр.].
Отделяй обязательное требование от рекомендации. Если подтверждающего фрагмента
недостаточно, прямо скажи, какого параметра или условия не хватает, и не называй число.
Не составляй отдельный список веб-ссылок: приложение добавит проверенные ссылки само.
В конце добавь: «Перед применением проверьте актуальность официальной редакции документа.»"""


def _citation(hit: SearchHit) -> str:
    citation = hit.document
    if hit.section:
        citation += f", {_section_label(hit.section)}"
    if hit.page:
        citation += f", стр. {hit.page}"
    return citation


def _source_footer(hits: list[SearchHit]) -> str:
    lines = ["🔗 Проверенные источники:"]
    seen = set()
    for hit in hits:
        key = (hit.document, hit.section, hit.page, hit.source_url)
        if key in seen:
            continue
        seen.add(key)
        line = f"• {_citation(hit)}"
        if hit.source_url:
            line += f"\n  {hit.source_url}"
        lines.append(line)
        if len(lines) >= 5:
            break
    return "\n".join(lines)


def _with_source_footer(answer: str, hits: list[SearchHit], limit: int = 4090) -> str:
    footer = _source_footer(hits)
    separator = "\n\n"
    available = limit - len(separator) - len(footer)
    if available < 200:
        return footer[:limit]
    body = answer.strip()
    if len(body) > available:
        body = body[: available - 1].rstrip(" ,;:-") + "…"
    return f"{body}{separator}{footer}"


def _section_label(section: str) -> str:
    normalized = section.strip().lower()
    if normalized.startswith(("статья", "раздел", "таблица", "приложение", "пункт", "п.")):
        return section.strip()
    return f"пункт {section.strip()}"


def _context(hits: list[SearchHit]) -> str:
    blocks = []
    for index, hit in enumerate(hits, 1):
        evidence_type = "Фрагмент нормативного пункта" if hit.kind == "clause" else "Карточка документа"
        location = f"стр. {hit.page}" if hit.page else "страница не определена"
        if hit.section:
            location += f", {_section_label(hit.section)}"
        source = f"\nОфициальный источник: {hit.source_url}" if hit.source_url else ""
        blocks.append(
            f"Источник {index}\nТип: {evidence_type}\nДокумент: {hit.document}\n"
            f"{location}{source}\n{hit.text}"
        )
    return "\n\n".join(blocks)


def _is_quantitative_question(question: str) -> bool:
    normalized = question.lower().replace("ё", "е")
    return any(
        marker in normalized
        for marker in (
            "сколько", "допуск", "отклон", "размер", "толщин", "высот", "ширин",
            "длин", "расстояни", "уклон", "шаг", "срок", "температур", "расход",
            "нагрузк", "усили", "процент", "мм", "см", "метр",
        )
    )


def _catalog_answer(question: str, hits: list[SearchHit]) -> str:
    blocks = ["🧭 По вопросу подобраны применимые нормативные документы:"]
    seen = set()
    selected = []
    best_score = max((hit.score for hit in hits), default=0.0)
    for hit in hits:
        if hit.document in seen:
            continue
        if selected and best_score > 0 and hit.score < best_score * 0.55:
            continue
        seen.add(hit.document)
        selected.append(hit)
        if len(selected) >= 3:
            break

    for hit in selected:
        block = f"\n• {hit.document}\nЧто регулирует: {hit.text}"
        if hit.status:
            block += f"\nСтатус: {hit.status}"
        if hit.edition:
            block += f"; {hit.edition}" if hit.status else f"\nРедакция: {hit.edition}"
        if hit.source_url:
            block += f"\nОфициальная карточка: {hit.source_url}"
        blocks.append(block)

    quantitative = _is_quantitative_question(question)
    if quantitative:
        blocks.append(
            "\nТочное значение и номер пункта не называю: по этому вопросу сейчас найдена "
            "карточка документа, но не загружен подтверждающий фрагмент пункта. Это защищает "
            "от выдуманного допуска."
        )
    else:
        blocks.append(
            "\nЭто подбор по области применения документов. Для цитаты конкретного требования "
            "нужны объект, операция и проверяемый параметр."
        )

    categories = [hit.category for hit in selected if hit.category]
    clarification = next(
        (CATEGORY_CLARIFICATIONS[category] for category in categories if category in CATEGORY_CLARIFICATIONS),
        "Укажите объект, вид работ, конструктивный элемент и нужный параметр.",
    )
    blocks.extend(
        [
            f"\nРекомендация: {clarification}",
            "Перед применением проверьте актуальность официальной редакции документа.",
        ]
    )
    return "\n".join(blocks)[:4000]


def _best_excerpt(question: str, text: str, maximum: int = 620) -> str:
    profile = analyze_query(question)
    sentences = [part.strip() for part in re.split(r"(?<=[.!?])\s+|\n+", text) if len(part.strip()) >= 35]
    ranked = sorted(
        enumerate(sentences),
        key=lambda item: (-text_relevance(profile, item[1]), item[0]),
    )
    chosen = sorted(ranked[:2], key=lambda item: item[0])
    excerpt = " ".join(sentence for _, sentence in chosen) or text.strip()
    if len(excerpt) > maximum:
        excerpt = excerpt[: maximum - 1].rstrip(" ,;:-") + "…"
    return excerpt


def local_answer(question: str, hits: list[SearchHit]) -> str:
    if not hits:
        return (
            "В загруженной нормативной базе не найдено достаточно данных для надёжного ответа. "
            "Уточните объект, вид работ, конструктивный элемент и нужный параметр.\n\n"
            "Перед применением проверьте актуальность официальной редакции документа."
        )

    clause_hits = [hit for hit in hits if hit.kind == "clause"]
    catalog_hits = [hit for hit in hits if hit.kind == "catalog"]
    if not clause_hits:
        return _catalog_answer(question, catalog_hits)

    blocks = ["🧠 Бесплатный локальный поиск нашёл подтверждённые нормативные фрагменты:"]
    seen = set()
    for hit in clause_hits[:5]:
        excerpt = _best_excerpt(question, hit.text)
        fingerprint = re.sub(r"\W+", "", excerpt.lower())[:160]
        if not excerpt or fingerprint in seen:
            continue
        seen.add(fingerprint)
        citation = hit.document
        if hit.section:
            citation += f", {_section_label(hit.section)}"
        if hit.page:
            citation += f", стр. {hit.page}"
        block = f"\n• {excerpt}\n[{citation}]"
        if hit.edition:
            block += f"\nРедакция: {hit.edition}"
        if hit.source_url:
            block += f"\nИсточник: {hit.source_url}"
        blocks.append(block)

    if catalog_hits:
        blocks.append("\nСвязанные документы:")
        for hit in catalog_hits[:2]:
            related = f"• {hit.document}"
            if hit.source_url:
                related += f" — {hit.source_url}"
            blocks.append(related)

    blocks.append(
        "\nРекомендация: сверяйте численное требование с указанным пунктом и официальной редакцией. "
        "Бот не подставляет отсутствующие в тексте нормы."
    )
    answer = "\n".join(blocks)
    return answer[:4000]


async def _generate_openai(api_key: str, model: str, prompt: str) -> str:
    from openai import AsyncOpenAI

    client = AsyncOpenAI(api_key=api_key, timeout=30.0, max_retries=1)
    response = await client.responses.create(
        model=model,
        instructions=SYSTEM_PROMPT,
        input=prompt,
        reasoning={"effort": "low"},
        text={"verbosity": "low"},
        max_output_tokens=700,
        store=False,
    )
    return response.output_text.strip()


async def _generate_groq(api_key: str, model: str, fallback_model: str, prompt: str) -> str:
    from openai import AsyncOpenAI

    client = AsyncOpenAI(
        api_key=api_key,
        base_url="https://api.groq.com/openai/v1",
        timeout=30.0,
        max_retries=0,
    )
    models = list(dict.fromkeys(candidate for candidate in (model, fallback_model) if candidate))
    last_error: Exception | None = None
    for candidate in models:
        try:
            response = await client.chat.completions.create(
                model=candidate,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.1,
                max_completion_tokens=700,
            )
            return (response.choices[0].message.content or "").strip()
        except Exception as error:
            last_error = error
            logger.warning("Groq model %s unavailable: %s", candidate, type(error).__name__)
    if last_error:
        raise last_error
    raise ValueError("No Groq model configured")


async def answer_question(
    api_key: str,
    model: str,
    question: str,
    hits: list[SearchHit],
    *,
    provider: str = "openai",
    fallback_model: str = "",
) -> str:
    if not hits:
        return local_answer(question, hits)
    clause_hits = [hit for hit in hits if hit.kind == "clause"]
    if not api_key:
        return local_answer(question, hits)
    if not clause_hits and _is_quantitative_question(question):
        return local_answer(question, hits)
    evidence_hits = clause_hits[:6] if clause_hits else [hit for hit in hits if hit.kind == "catalog"][:5]
    prompt = f"Вопрос пользователя:\n{question}\n\nДанные нормативной базы:\n{_context(evidence_hits)}"
    try:
        if provider == "groq":
            generated = await _generate_groq(api_key, model, fallback_model, prompt)
        else:
            generated = await _generate_openai(api_key, model, prompt)
        if not generated:
            raise ValueError(f"{provider} returned an empty answer")
        return _with_source_footer(generated, evidence_hits)
    except Exception as error:
        logger.warning(
            "%s answer generation unavailable; using free local answer: %s",
            provider,
            type(error).__name__,
        )
        return local_answer(question, hits)

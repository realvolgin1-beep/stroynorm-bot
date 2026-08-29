import logging
import re

from app.search import SearchHit
from app.smart_search import analyze_query, text_relevance


logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """Ты — справочный помощник по строительным СП и ГОСТам РФ.
Отвечай только на основании переданных фрагментов нормативных документов.
Не придумывай нормы, номера пунктов, значения и статусы документов.
Если данных недостаточно, прямо скажи об этом и предложи уточнить запрос.
Для каждого существенного утверждения укажи источник в формате [Документ, пункт, стр.].
Отделяй обязательное требование от рекомендации. В конце всегда добавляй:
«Перед применением проверьте актуальность официальной редакции документа.»"""


def _context(hits: list[SearchHit]) -> str:
    blocks = []
    for index, hit in enumerate(hits, 1):
        location = f"стр. {hit.page}" if hit.page else "страница не определена"
        if hit.section:
            location += f", пункт/раздел {hit.section}"
        source = f"\nОфициальный источник: {hit.source_url}" if hit.source_url else ""
        blocks.append(f"Фрагмент {index}\nДокумент: {hit.document}\n{location}{source}\n{hit.text}")
    return "\n\n".join(blocks)


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

    blocks = ["🧠 Бесплатный локальный поиск нашёл нормативные фрагменты:"]
    seen = set()
    for hit in hits[:5]:
        excerpt = _best_excerpt(question, hit.text)
        fingerprint = re.sub(r"\W+", "", excerpt.lower())[:160]
        if not excerpt or fingerprint in seen:
            continue
        seen.add(fingerprint)
        citation = hit.document
        if hit.section:
            citation += f", пункт {hit.section}"
        if hit.page:
            citation += f", стр. {hit.page}"
        block = f"\n• {excerpt}\n[{citation}]"
        if hit.edition:
            block += f"\nРедакция: {hit.edition}"
        if hit.source_url:
            block += f"\nИсточник: {hit.source_url}"
        blocks.append(block)

    blocks.append(
        "\nРекомендация: сверяйте численное требование с указанным пунктом и официальной редакцией. "
        "Бот не подставляет отсутствующие в тексте нормы."
    )
    answer = "\n".join(blocks)
    return answer[:4000]


async def answer_question(api_key: str, model: str, question: str, hits: list[SearchHit]) -> str:
    if not hits:
        return local_answer(question, hits)
    if not api_key:
        return local_answer(question, hits)
    try:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=api_key, timeout=18.0, max_retries=0)
        response = await client.responses.create(
            model=model,
            instructions=SYSTEM_PROMPT,
            input=f"Вопрос пользователя:\n{question}\n\nФрагменты базы:\n{_context(hits)}",
            temperature=0.1,
            max_output_tokens=900,
        )
        return response.output_text.strip()
    except Exception as error:
        logger.warning("External answer generation unavailable; using free local answer: %s", type(error).__name__)
        return local_answer(question, hits)

from openai import AsyncOpenAI

from app.search import SearchHit


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
        blocks.append(f"Фрагмент {index}\nДокумент: {hit.document}\n{location}\n{hit.text}")
    return "\n\n".join(blocks)


async def answer_question(api_key: str, model: str, question: str, hits: list[SearchHit]) -> str:
    if not hits:
        return (
            "В загруженной нормативной базе не найдено достаточно данных для надёжного ответа. "
            "Уточните объект и требование: автомобильная дорога или мост, вид работ, конструктивный элемент, "
            "измеряемый параметр и предполагаемый документ.\n\n"
            "Перед применением проверьте актуальность официальной редакции документа."
        )
    if not api_key:
        excerpts = []
        for hit in hits[:5]:
            source = hit.document
            if hit.section:
                source += f", пункт {hit.section}"
            if hit.page:
                source += f", стр. {hit.page}"
            excerpts.append(f"• {hit.text[:500].strip()}\n[{source}]")
        return (
            "Нашёл подходящие фрагменты:\n\n"
            + "\n\n".join(excerpts)
            + "\n\nПеред применением проверьте актуальность официальной редакции документа."
        )
    client = AsyncOpenAI(api_key=api_key)
    response = await client.responses.create(
        model=model,
        instructions=SYSTEM_PROMPT,
        input=f"Вопрос пользователя:\n{question}\n\nФрагменты базы:\n{_context(hits)}",
        temperature=0.1,
        max_output_tokens=900,
    )
    return response.output_text.strip()

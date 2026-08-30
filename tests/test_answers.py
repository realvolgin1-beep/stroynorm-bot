import asyncio
import sys
from types import SimpleNamespace

from app.answers import answer_question, local_answer
from app.search import SearchHit


def test_local_answer_contains_clause_page_and_link():
    answer = local_answer(
        "ширина эвакуационного выхода",
        [
            SearchHit(
                document="СП 1.13130.2020",
                page=12,
                section="4.2.5",
                text="Ширина эвакуационного выхода определяется расчетом. Требование проверяют по проекту.",
                score=2.0,
                source_url="https://protect.gost.ru/sp/details/example",
                edition="действующая редакция",
            )
        ],
    )

    assert "пункт 4.2.5" in answer
    assert "стр. 12" in answer
    assert "https://protect.gost.ru/sp/details/example" in answer


def test_local_answer_preserves_article_label():
    answer = local_answer(
        "требования закона",
        [SearchHit("Федеральный закон", 3, "Статья 6", "Требование применяется к объектам строительства.", 1.0)],
    )

    assert "Статья 6" in answer
    assert "пункт Статья" not in answer


def test_catalog_answer_links_document_and_does_not_invent_tolerance():
    answer = local_answer(
        "допустимая толщина штукатурки",
        [
            SearchHit(
                document="СП 71.13330.2017 «Изоляционные и отделочные покрытия»",
                page=None,
                section="область применения",
                text="Производство и контроль штукатурных работ.",
                score=20.0,
                source_url="https://protect.gost.ru/sp/details/example",
                edition="действующая редакция",
                kind="catalog",
                category="finishes",
                status="действует",
            )
        ],
    )

    assert "СП 71.13330.2017" in answer
    assert "https://protect.gost.ru/sp/details/example" in answer
    assert "Точное значение и номер пункта не называю" in answer
    assert "±" not in answer


def test_openai_answer_uses_luna_controls_and_appends_verified_source(monkeypatch):
    captured = {}

    class FakeResponses:
        async def create(self, **kwargs):
            captured.update(kwargs)
            return SimpleNamespace(
                output_text="Допустимое отклонение составляет 10 мм [СП 70.13330.2012, таблица 5.12, стр. 42]."
            )

    class FakeAsyncOpenAI:
        def __init__(self, **kwargs):
            captured["client"] = kwargs
            self.responses = FakeResponses()

    monkeypatch.setitem(sys.modules, "openai", SimpleNamespace(AsyncOpenAI=FakeAsyncOpenAI))
    hit = SearchHit(
        document="СП 70.13330.2012",
        page=42,
        section="таблица 5.12",
        text="Предельное отклонение положения элемента составляет 10 мм.",
        score=5.0,
        source_url="https://protect.gost.ru/document/example",
    )

    answer = asyncio.run(
        answer_question("sk-test", "gpt-5.6-luna", "Какой допуск?", [hit])
    )

    assert captured["model"] == "gpt-5.6-luna"
    assert captured["reasoning"] == {"effort": "low"}
    assert captured["text"] == {"verbosity": "low"}
    assert captured["max_output_tokens"] == 700
    assert captured["store"] is False
    assert "temperature" not in captured
    assert "🔗 Проверенные источники" in answer
    assert "https://protect.gost.ru/document/example" in answer


def test_openai_failure_falls_back_to_grounded_local_answer(monkeypatch):
    class FailingResponses:
        async def create(self, **kwargs):
            raise RuntimeError("provider unavailable")

    class FakeAsyncOpenAI:
        def __init__(self, **kwargs):
            self.responses = FailingResponses()

    monkeypatch.setitem(sys.modules, "openai", SimpleNamespace(AsyncOpenAI=FakeAsyncOpenAI))
    hit = SearchHit(
        document="СП 70.13330.2012",
        page=42,
        section="таблица 5.12",
        text="Предельное отклонение положения элемента составляет 10 мм.",
        score=5.0,
        source_url="https://protect.gost.ru/document/example",
    )

    answer = asyncio.run(answer_question("sk-test", "gpt-5.6-luna", "Какой допуск?", [hit]))

    assert "Бесплатный локальный поиск" in answer
    assert "https://protect.gost.ru/document/example" in answer


def test_groq_answer_uses_free_primary_model_and_appends_source(monkeypatch):
    captured = {}

    class FakeCompletions:
        async def create(self, **kwargs):
            captured.update(kwargs)
            return SimpleNamespace(
                choices=[
                    SimpleNamespace(
                        message=SimpleNamespace(
                            content="Монтаж выполняют по проекту производства работ."
                        )
                    )
                ]
            )

    class FakeAsyncOpenAI:
        def __init__(self, **kwargs):
            captured["client"] = kwargs
            self.chat = SimpleNamespace(completions=FakeCompletions())

    monkeypatch.setitem(sys.modules, "openai", SimpleNamespace(AsyncOpenAI=FakeAsyncOpenAI))
    hit = SearchHit(
        document="СП 70.13330.2012",
        page=42,
        section="5.1.3",
        text="Монтаж конструкций выполняют в соответствии с проектом производства работ.",
        score=5.0,
        source_url="https://protect.gost.ru/document/example",
    )

    answer = asyncio.run(
        answer_question(
            "gsk-test",
            "qwen/qwen3.8-27b",
            "Как выполнять монтаж колонн?",
            [hit],
            provider="groq",
            fallback_model="openai/gpt-oss-120b",
        )
    )

    assert captured["client"]["base_url"] == "https://api.groq.com/openai/v1"
    assert captured["model"] == "qwen/qwen3.8-27b"
    assert captured["temperature"] == 0.1
    assert captured["max_completion_tokens"] == 700
    assert "🔗 Проверенные источники" in answer
    assert "https://protect.gost.ru/document/example" in answer


def test_groq_tries_fallback_model_after_primary_failure(monkeypatch):
    attempted = []

    class FakeCompletions:
        async def create(self, **kwargs):
            attempted.append(kwargs["model"])
            if len(attempted) == 1:
                raise RuntimeError("primary unavailable")
            return SimpleNamespace(
                choices=[
                    SimpleNamespace(
                        message=SimpleNamespace(content="Ответ по подтверждённому фрагменту.")
                    )
                ]
            )

    class FakeAsyncOpenAI:
        def __init__(self, **kwargs):
            self.chat = SimpleNamespace(completions=FakeCompletions())

    monkeypatch.setitem(sys.modules, "openai", SimpleNamespace(AsyncOpenAI=FakeAsyncOpenAI))
    hit = SearchHit("СП 70.13330.2012", 42, "5.1.3", "Подтверждённый текст пункта.", 5.0)

    answer = asyncio.run(
        answer_question(
            "gsk-test",
            "qwen/qwen3.8-27b",
            "Как выполнять монтаж?",
            [hit],
            provider="groq",
            fallback_model="openai/gpt-oss-120b",
        )
    )

    assert attempted == ["qwen/qwen3.8-27b", "openai/gpt-oss-120b"]
    assert "Ответ по подтверждённому фрагменту" in answer


def test_quantitative_catalog_question_never_calls_external_model(monkeypatch):
    class ForbiddenAsyncOpenAI:
        def __init__(self, **kwargs):
            raise AssertionError("external model must not be called")

    monkeypatch.setitem(sys.modules, "openai", SimpleNamespace(AsyncOpenAI=ForbiddenAsyncOpenAI))
    hit = SearchHit(
        document="СП 70.13330.2012",
        page=None,
        section="область применения",
        text="Монтаж несущих конструкций.",
        score=5.0,
        source_url="https://protect.gost.ru/document/example",
        kind="catalog",
    )

    answer = asyncio.run(
        answer_question(
            "gsk-test",
            "qwen/qwen3.8-27b",
            "Какой допуск отклонения колонны?",
            [hit],
            provider="groq",
        )
    )

    assert "Точное значение и номер пункта не называю" in answer
    assert "±" not in answer


def test_qualitative_catalog_question_can_use_groq(monkeypatch):
    captured = {}

    class FakeCompletions:
        async def create(self, **kwargs):
            captured.update(kwargs)
            return SimpleNamespace(
                choices=[
                    SimpleNamespace(
                        message=SimpleNamespace(
                            content="Для монтажа колонн применяют требования указанного СП и ППР."
                        )
                    )
                ]
            )

    class FakeAsyncOpenAI:
        def __init__(self, **kwargs):
            self.chat = SimpleNamespace(completions=FakeCompletions())

    monkeypatch.setitem(sys.modules, "openai", SimpleNamespace(AsyncOpenAI=FakeAsyncOpenAI))
    hit = SearchHit(
        document="СП 70.13330.2012",
        page=None,
        section="область применения",
        text="Производство и приёмка работ по монтажу несущих конструкций.",
        score=5.0,
        source_url="https://protect.gost.ru/document/example",
        kind="catalog",
    )

    answer = asyncio.run(
        answer_question(
            "gsk-test",
            "qwen/qwen3.8-27b",
            "Расскажи про монтаж колонн",
            [hit],
            provider="groq",
        )
    )

    assert "Карточка документа" in captured["messages"][1]["content"]
    assert "Для монтажа колонн" in answer
    assert "https://protect.gost.ru/document/example" in answer

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

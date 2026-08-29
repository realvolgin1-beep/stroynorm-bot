from app.answers import local_answer
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

import sqlite3

from app.search import search


def test_search_returns_matching_fragment(tmp_path):
    database = tmp_path / "test.db"
    with sqlite3.connect(database) as connection:
        connection.execute(
            "CREATE VIRTUAL TABLE chunks USING fts5(document, page UNINDEXED, section UNINDEXED, text, tokenize='unicode61')"
        )
        connection.execute(
            "INSERT INTO chunks VALUES (?, ?, ?, ?)",
            ("СП 1.13130", 12, "4.2.5", "Ширина эвакуационного выхода определяется расчетом."),
        )
    hits = search(str(database), "ширина эвакуационного выхода")
    assert hits
    assert hits[0].document == "СП 1.13130"
    assert hits[0].page == 12


def test_search_understands_bridge_word_form_and_returns_source(tmp_path):
    database = tmp_path / "test.db"
    with sqlite3.connect(database) as connection:
        connection.execute(
            "CREATE VIRTUAL TABLE chunks USING fts5("
            "document, page UNINDEXED, section UNINDEXED, text, "
            "source_url UNINDEXED, edition UNINDEXED, tokenize='unicode61')"
        )
        connection.execute(
            "INSERT INTO chunks VALUES (?, ?, ?, ?, ?, ?)",
            (
                "СП 35.13330.2011 Мосты и трубы",
                41,
                "7.12",
                "Требования к монтажу пролетных строений и контролю положения опор.",
                "https://protect.gost.ru/sp/details/example",
                "действующая редакция",
            ),
        )
    hits = search(str(database), "пролётное строение моста")
    assert hits
    assert hits[0].section == "7.12"
    assert hits[0].source_url == "https://protect.gost.ru/sp/details/example"


def test_search_routes_question_without_sqlite_database():
    hits = search("/missing/stroynorm.db", "толщина штукатурки")

    assert hits
    assert hits[0].kind == "catalog"
    assert hits[0].document.startswith("СП 71.13330.2017")
    assert hits[0].source_url

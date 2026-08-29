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

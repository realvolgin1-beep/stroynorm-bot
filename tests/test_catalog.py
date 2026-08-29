from app.catalog import documents, search_catalog


def test_bridge_component_query_finds_bridge_documents():
    hits = search_catalog("Пролетное строение")

    codes = {document["code"] for document in hits}
    assert hits[0]["code"] == "СП 35.13330.2011"
    assert hits[1]["code"] == "ГОСТ 33384-2015"
    assert "СП 35.13330.2011" in codes
    assert "ГОСТ 33384-2015" in codes


def test_road_sign_query_finds_traffic_standard():
    hits = search_catalog("установка дорожных знаков")

    assert hits[0]["code"] == "ГОСТ Р 52289-2019"


def test_typo_in_bridge_query_is_understood():
    hits = search_catalog("пролтное строние")

    assert hits[0]["code"] == "СП 35.13330.2011"


def test_fire_query_finds_evacuation_rules():
    hits = search_catalog("ширина эвакуационного выхода")

    assert hits[0]["code"] == "СП 1.13130.2020"


def test_masonry_query_finds_masonry_rules():
    hits = search_catalog("кирпичная кладка")

    assert hits[0]["code"] == "СП 15.13330.2020"


def test_sp46_compact_number_finds_bridge_construction_rules():
    hits = search_catalog("СП46")

    assert hits[0]["code"] == "СП 46.13330.2012"


def test_every_catalog_document_has_searchable_scope_and_source():
    assert len(documents()) == 81
    assert all(document.get("scope") for document in documents())
    assert all(document.get("official_url") for document in documents())


def test_general_construction_questions_route_to_profile_documents():
    cases = {
        "толщина штукатурки": "СП 71.13330.2017",
        "допуск монтажа колонн": "СП 70.13330.2012",
        "защитный слой бетона": "СП 63.13330.2018",
        "уклон канализационной трубы": "СП 30.13330.2020",
        "расстояние между пожарными гидрантами": "СП 8.13130.2020",
        "размер пандуса для инвалидов": "СП 59.13330.2020",
        "минимальная освещенность лестницы": "СП 52.13330.2016",
        "опрессовка системы отопления": "СП 73.13330.2016",
        "глубина заложения фундамента": "СП 22.13330.2016",
        "трещины в здании обследование": "ГОСТ 31937-2024",
    }

    for question, expected in cases.items():
        hits = search_catalog(question)
        assert hits[0]["code"] == expected, question

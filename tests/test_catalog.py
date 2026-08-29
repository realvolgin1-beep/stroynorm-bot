from app.catalog import search_catalog


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

from scripts.ingest import section_for


def test_section_for_reads_normative_clause():
    assert section_for("7.12 Требования к конструкции") == "7.12"


def test_section_for_reads_legal_article():
    assert section_for("Статья 6 Требования безопасности") == "Статья 6"


def test_section_for_reads_table_reference():
    assert section_for("Таблица 5.2 Допустимые отклонения") == "Таблица 5.2"

"""Análisis puro de variedades: normalización, grafías unificadas y casi-duplicados."""
from apps.backend.src.core.variety_analysis import analyze_varieties, edit_distance, normalize_variety


def test_normalize_ignores_case_whitespace_and_accents():
    assert normalize_variety("  Légacy ") == "legacy"
    assert normalize_variety("Duke   Blue") == "duke blue"
    assert normalize_variety("BILOXI") == normalize_variety("biloxi")


def test_edit_distance():
    assert edit_distance("biloxi", "biloxi") == 0
    assert edit_distance("biloxi", "biloxy") == 1
    assert edit_distance("duke", "dukes") == 1
    assert edit_distance("kitten", "sitting") == 3
    assert edit_distance("", "ab") == 2


def test_counts_group_by_normalized_name_and_merged_spellings_are_listed():
    report = analyze_varieties(["Biloxi", " biloxi ", "BILOXI", "Légacy", "Legacy", "Duke"])
    assert report.counts == {"biloxi": 3, "legacy": 2, "duke": 1}
    assert set(report.spellings["biloxi"]) == {"Biloxi", " biloxi ", "BILOXI"}
    assert report.merged == ["biloxi", "legacy"]  # "duke" solo tiene una grafía


def test_near_duplicates_are_distinct_normalized_names_within_distance_2():
    report = analyze_varieties(["Biloxi", "Biloxy", "Bilxy", "Duke", "Emerald Blue"])
    assert ("biloxi", "biloxy") in report.near_duplicates
    assert ("biloxy", "bilxy") in report.near_duplicates
    assert ("biloxi", "bilxy") in report.near_duplicates  # distancia 2
    assert not any("duke" in pair or "emerald blue" in pair for pair in report.near_duplicates)


def test_empty_input_gives_empty_report():
    report = analyze_varieties([])
    assert report.counts == {} and report.merged == [] and report.near_duplicates == []

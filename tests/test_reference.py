from crs_assistant import reference


def test_all_47_counties_present_with_unique_codes():
    counties = reference.counties()
    assert len(counties) == 47
    assert len({c["code"] for c in counties}) == 47


def test_county_lookup_pads_code():
    assert reference.county_by_code("47")["name"] == "Nairobi"
    assert reference.county_by_code("999") is None


def test_every_document_is_bilingual():
    for doc_id, entry in reference.documents().items():
        assert entry["en"], doc_id
        assert entry["sw"], doc_id


def test_document_name_falls_back_to_english():
    assert reference.document_name("mother_id", "fr") == reference.document_name("mother_id", "en")

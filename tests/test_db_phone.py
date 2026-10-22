import pytest

from crs_assistant import db, phone


@pytest.mark.parametrize(
    "raw",
    ["0712345678", "+254712345678", "254712345678", "712345678", "0712 345 678", "0112345678"],
)
def test_normalise_accepts_common_formats(raw):
    assert phone.normalise(raw).startswith("+254")
    assert len(phone.normalise(raw)) == 13


@pytest.mark.parametrize("raw", ["", "12345", "0812345678", "+255712345678", "07123456789"])
def test_normalise_rejects_invalid(raw):
    with pytest.raises(phone.InvalidPhone):
        phone.normalise(raw)


def test_mask_hides_middle_digits():
    assert phone.mask("+254712345678") == "+254712***678"


def test_connect_seeds_one_office_per_county_once():
    conn = db.connect()
    assert conn.execute("SELECT COUNT(*) FROM offices").fetchone()[0] == 47
    db._seed_offices(conn)
    assert conn.execute("SELECT COUNT(*) FROM offices").fetchone()[0] == 47

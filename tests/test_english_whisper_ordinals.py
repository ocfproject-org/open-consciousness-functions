import pytest
from ocf_tools import speech_verify as sv

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    ("digits", "spoken"),
    [
        ("1st", "first"),
        ("2nd", "second"),
        ("3rd", "third"),
        ("10th", "tenth"),
        ("11th", "eleventh"),
        ("12th", "twelfth"),
        ("13th", "thirteenth"),
        ("20th", "twentieth"),
        ("21st", "twenty-first"),
        ("22nd", "twenty second"),
        ("23rd", "twenty-third"),
        ("40th", "fortieth"),
        ("99th", "ninety ninth"),
    ],
)
def test_exact_english_ordinal_typography(digits, spoken):
    assert sv.normalized_words(f"the {digits} state", "en") == sv.normalized_words(
        f"the {spoken} state", "en"
    )


@pytest.mark.parametrize(
    "different", ["twenty", "20", "20st", "20nd", "20rd", "020th", "twentieths", "20 th"]
)
def test_cardinal_or_malformed_spelling_does_not_equal_twentieth(different):
    assert sv.normalized_words(different, "en") != sv.normalized_words("twentieth", "en")


def test_non_english_unchanged_and_protected_cue_fingerprints_unchanged():
    assert sv.normalized_words("20th", "fr") == ("20th",)
    assert (
        sv._json_sha256(
            sv.normalized_words("Think or say in your mind, plus release 11 access.", "en")
        )
        == sv._ACCESS_EXACT_WORDS
    )
    assert (
        sv._json_sha256(
            sv.normalized_words("Think or say in your mind, plus release 11-axis.", "en")
        )
        == sv._ACCESS_PRIMARY_WRONG_WORDS
    )
    assert sv.normalized_words("Access", "en") != sv.normalized_words("Axis", "en")


@pytest.mark.parametrize(
    ("different", "ordinal"),
    [
        ("11st", "eleventh"),
        ("13rd", "thirteenth"),
        ("21nd", "twenty first"),
        ("21st", "twentieth"),
        ("22nd", "twenty first"),
        ("21", "twenty first"),
    ],
)
def test_wrong_suffix_number_or_type_is_not_equal(different, ordinal):
    assert sv.normalized_words(different, "en") != sv.normalized_words(ordinal, "en")

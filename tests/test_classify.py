import pytest

from screener.classify import classify, is_environmental_claim, rate_sentence
from screener.extract import split_sentences

CASES = [
    ("This watch is carbon neutral thanks to high-quality carbon credits from forestry projects.", "OFFSET_NEUTRALITY"),
    ("We offset all remaining emissions, which makes our shipping climate neutral.", "OFFSET_NEUTRALITY"),
    ("Our new collection is eco-friendly and kind to the planet.", "GENERIC"),
    ("We offer sustainable products for a greener future.", "GENERIC"),
    ("All our products have zero environmental impact.", "OVERSTATED"),
    ("Our flagship store is fully sustainable.", "OVERSTATED"),
    ("Our offices are carbon neutral.", "NEUTRALITY_UNSUPPORTED"),
    ("We aim to become net zero by 2040.", "FUTURE_NO_PLAN"),
    ("We will make our packaging more recyclable in the coming years.", "FUTURE_NO_PLAN"),
    ("We will cut Scope 1 and 2 emissions by 50% by 2030 versus 2019, a target validated by the SBTi.", "FUTURE_WITH_PLAN"),
    ("In 2025, 78% of the electricity used in our factories came from renewable sources.", "SPECIFIC"),
    ("We reduced water use per product by 12% compared with 2022.", "SPECIFIC"),
    ("Our operations emitted 1.2 million tCO2e in 2025.", "SPECIFIC"),
    ("We are committed to protecting the environment in everything we do.", "VAGUE"),
    ("Sustainability is at the heart of our brand.", "VAGUE"),
]


@pytest.mark.parametrize("text,expected", CASES)
def test_categories(text, expected):
    assert is_environmental_claim(text), text
    assert classify(text).category == expected


@pytest.mark.parametrize("text", [
    "Climate change may increase the frequency of extreme weather events in Asia.",
    "The board met eleven times during the financial year to discuss strategy.",
    "What does net zero mean for the fashion industry?",
])
def test_not_a_claim(text):
    assert not rate_sentence(text).is_claim


def test_green_electricity_is_not_generic():
    r = classify("Our stores in Germany use green electricity supplied under long-term contracts.")
    assert r.category != "GENERIC"


def test_sentence_splitter_keeps_decimals():
    parts = split_sentences("Emissions fell by 2.5% in 2025. We aim for more, e.g. in logistics.")
    assert parts == ["Emissions fell by 2.5% in 2025.", "We aim for more, e.g. in logistics."]


def test_negated_offset_is_not_offset_neutrality():
    assert classify("Our factories are carbon neutral without using offsets.").category != "OFFSET_NEUTRALITY"
    assert classify("We do not use carbon credits to claim that our shoes are climate neutral.").category != "OFFSET_NEUTRALITY"

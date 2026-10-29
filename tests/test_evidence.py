import pytest

from screener.evidence import check_evidence, evidence_score


def found(text):
    return {h.key for h in check_evidence([text]) if h.found}


@pytest.mark.parametrize("text,key", [
    ("Scope 1 emissions\ntCO2e\n31,500\n18,400", "scope1"),
    ("Our Scope 1 and 2 emissions amounted to 182,000 tCO2e in 2025.", "scope2"),
    ("Scope 3 emissions: 1,240,000 tCO2e", "scope3"),
    ("Emission intensity: 12.4 tCO2e per EUR million revenue", "intensity"),
    ("Emissions fell by 31% compared with 2019.", "base_year"),
    ("Our target was validated by the Science Based Targets initiative.", "sbti"),
    ("We published our climate transition plan in 2025.", "transition_plan"),
    ("In 2025 we retired 12,000 tonnes of carbon credits.", "credits"),
    ("We do not use carbon credits to meet our targets.", "credits"),
    ("The GHG data received limited assurance under ISAE 3410.", "assurance"),
    ("See the GRI content index at the end of this report.", "gri_index"),
])
def test_detects(text, key):
    assert key in found(text)


@pytest.mark.parametrize("text,key", [
    ("We will cut Scope 3 emissions by 40% by 2030.", "scope3"),          # a target is not a disclosure
    ("Our shop is climate neutral thanks to carbon credits.", "credits"),  # no quantity
])
def test_does_not_overcount(text, key):
    assert key not in found(text)


def test_score_range():
    assert evidence_score(check_evidence(["nothing relevant here"])) == 0.0

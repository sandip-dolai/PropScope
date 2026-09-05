"""
Part 6.3 – Recommendation Explanation Generator Tests

Validates:
- classify_match_tier thresholds
- verdict_code mapping
- Per-dimension explanation generators (budget, bedroom, area, location)
- RecommendationExplainer.explain() enrichment
- RecommendationExplainer.explain_all() over a result list
- highlight / warning aggregation
- match_summary prose generation
"""

import pytest
from apps.recommendations.explainer import (
    classify_match_tier,
    verdict_code,
    generate_budget_explanation,
    generate_bedroom_explanation,
    generate_area_explanation,
    generate_location_explanation,
    generate_match_summary,
    RecommendationExplainer,
    MATCH_TIER_PRIME,
    MATCH_TIER_STRONG,
    MATCH_TIER_GOOD,
    MATCH_TIER_FAIR,
    MATCH_TIER_WEAK,
    VERDICT_EXCELLENT,
    VERDICT_GOOD,
    VERDICT_FAIR,
    VERDICT_POOR,
)


# ─── Match Tier Classification ────────────────────────────────────────────────

class TestClassifyMatchTier:
    def test_prime_at_threshold(self):
        assert classify_match_tier(88.0) == MATCH_TIER_PRIME

    def test_prime_above_threshold(self):
        assert classify_match_tier(95.0) == MATCH_TIER_PRIME

    def test_strong_at_threshold(self):
        assert classify_match_tier(74.0) == MATCH_TIER_STRONG

    def test_strong_below_prime(self):
        assert classify_match_tier(87.9) == MATCH_TIER_STRONG

    def test_good_at_threshold(self):
        assert classify_match_tier(60.0) == MATCH_TIER_GOOD

    def test_good_below_strong(self):
        assert classify_match_tier(73.9) == MATCH_TIER_GOOD

    def test_fair_at_threshold(self):
        assert classify_match_tier(45.0) == MATCH_TIER_FAIR

    def test_fair_below_good(self):
        assert classify_match_tier(59.9) == MATCH_TIER_FAIR

    def test_weak_below_fair(self):
        assert classify_match_tier(44.9) == MATCH_TIER_WEAK

    def test_weak_at_zero(self):
        assert classify_match_tier(0.0) == MATCH_TIER_WEAK


# ─── Verdict Codes ────────────────────────────────────────────────────────────

class TestVerdictCode:
    def test_excellent_at_threshold(self):
        assert verdict_code(85.0) == VERDICT_EXCELLENT

    def test_excellent_above(self):
        assert verdict_code(100.0) == VERDICT_EXCELLENT

    def test_good_at_threshold(self):
        assert verdict_code(65.0) == VERDICT_GOOD

    def test_good_below_excellent(self):
        assert verdict_code(84.9) == VERDICT_GOOD

    def test_fair_at_threshold(self):
        assert verdict_code(45.0) == VERDICT_FAIR

    def test_fair_below_good(self):
        assert verdict_code(64.9) == VERDICT_FAIR

    def test_poor_below_fair(self):
        assert verdict_code(44.9) == VERDICT_POOR

    def test_poor_at_zero(self):
        assert verdict_code(0.0) == VERDICT_POOR


# ─── Budget Explanation ───────────────────────────────────────────────────────

def fmt(amount):
    if amount >= 10000000:
        return f"₹{amount / 10000000:.2f} Cr"
    elif amount >= 100000:
        return f"₹{amount / 100000:.2f} L"
    return f"₹{int(amount):,}"


class TestGenerateBudgetExplanation:
    def test_excellent_score_is_highlight(self):
        expl = generate_budget_explanation(5000000, 8000000, 0, 92.0, fmt)
        assert expl["verdict"] == VERDICT_EXCELLENT
        assert expl["is_highlight"] is True
        assert expl["warning"] is None

    def test_good_score_is_highlight(self):
        expl = generate_budget_explanation(7500000, 8000000, 0, 72.0, fmt)
        assert expl["verdict"] == VERDICT_GOOD
        assert expl["is_highlight"] is True

    def test_fair_over_budget_has_warning(self):
        expl = generate_budget_explanation(8500000, 8000000, 0, 55.0, fmt)
        assert expl["is_highlight"] is False
        assert expl["warning"] is not None

    def test_poor_over_budget_has_warning(self):
        expl = generate_budget_explanation(15000000, 8000000, 0, 10.0, fmt)
        assert expl["verdict"] == VERDICT_POOR
        assert expl["warning"] is not None

    def test_dimension_key(self):
        expl = generate_budget_explanation(5000000, 8000000, 0, 90.0, fmt)
        assert expl["dimension"] == "budget"

    def test_score_is_rounded(self):
        expl = generate_budget_explanation(5000000, 8000000, 0, 91.23456, fmt)
        assert expl["score"] == 91.2


# ─── Bedroom Explanation ──────────────────────────────────────────────────────

class TestGenerateBedroomExplanation:
    def test_exact_match_is_highlight(self):
        expl = generate_bedroom_explanation(3, 3, 100.0)
        assert expl["verdict"] == VERDICT_EXCELLENT
        assert expl["is_highlight"] is True
        assert "Exactly" in expl["narrative"]

    def test_extra_room_is_highlight(self):
        expl = generate_bedroom_explanation(4, 3, 85.0)
        assert expl["is_highlight"] is True
        assert "extra" in expl["narrative"]

    def test_deficit_has_warning(self):
        expl = generate_bedroom_explanation(2, 3, 60.0)
        assert expl["is_highlight"] is False
        assert expl["warning"] is not None
        assert "fewer" in expl["narrative"]

    def test_large_deficit_poor_verdict(self):
        expl = generate_bedroom_explanation(1, 4, 10.0)
        assert expl["verdict"] == VERDICT_POOR

    def test_dimension_key(self):
        expl = generate_bedroom_explanation(3, 3, 100.0)
        assert expl["dimension"] == "bedroom"


# ─── Area Explanation ─────────────────────────────────────────────────────────

class TestGenerateAreaExplanation:
    def test_above_target_is_highlight(self):
        expl = generate_area_explanation(1200, 1000, 0, 95.0)
        assert expl["is_highlight"] is True
        assert "more" in expl["narrative"]

    def test_below_target_fair_has_warning(self):
        expl = generate_area_explanation(700, 1000, 0, 55.0)
        assert expl["warning"] is not None

    def test_meets_minimum_is_highlight(self):
        expl = generate_area_explanation(900, 0, 800, 100.0)
        assert expl["is_highlight"] is True

    def test_below_minimum_has_warning(self):
        expl = generate_area_explanation(600, 0, 800, 40.0)
        assert expl["warning"] is not None

    def test_no_area_data(self):
        expl = generate_area_explanation(0, 0, 0, 80.0)
        assert "not available" in expl["narrative"].lower()

    def test_dimension_key(self):
        expl = generate_area_explanation(1000, 0, 0, 85.0)
        assert expl["dimension"] == "area"


# ─── Location Explanation ─────────────────────────────────────────────────────

class TestGenerateLocationExplanation:
    def test_excellent_is_highlight(self):
        expl = generate_location_explanation(90.0, "Prime Connectivity")
        assert expl["is_highlight"] is True
        assert expl["warning"] is None

    def test_poor_has_warning(self):
        expl = generate_location_explanation(30.0, "Limited Accessibility")
        assert expl["is_highlight"] is False
        assert expl["warning"] is not None

    def test_strong_pillars_surfaced(self):
        breakdown = {
            "Transport": {"score": 92},
            "Healthcare": {"score": 30},
        }
        expl = generate_location_explanation(75.0, "Good Accessibility", breakdown)
        assert any("Transport" in p for p in expl["strong_pillars"])
        assert any("Healthcare" in p for p in expl["weak_pillars"])

    def test_dimension_key(self):
        expl = generate_location_explanation(80.0, "Good Connectivity")
        assert expl["dimension"] == "location"


# ─── Match Summary ────────────────────────────────────────────────────────────

class TestGenerateMatchSummary:
    def test_prime_prefix(self):
        summary = generate_match_summary(
            MATCH_TIER_PRIME, "My Property", 90.0, [], [], 3, 8000000, fmt
        )
        assert "Exceptional match" in summary

    def test_weak_prefix(self):
        summary = generate_match_summary(
            MATCH_TIER_WEAK, "My Property", 30.0, [], [], 2, 5000000, fmt
        )
        assert "Weak match" in summary

    def test_highlights_appended(self):
        summary = generate_match_summary(
            MATCH_TIER_GOOD, "My Property", 65.0,
            ["Within your budget"], [], 2, 5000000, fmt
        )
        assert "within your budget" in summary

    def test_warnings_appended(self):
        summary = generate_match_summary(
            MATCH_TIER_FAIR, "My Property", 50.0,
            [], ["1 BHK short of requirement"], 3, 6000000, fmt
        )
        assert "note" in summary.lower()


# ─── RecommendationExplainer Integration ─────────────────────────────────────

FIXTURE_RESULT = {
    "property_id": 101,
    "title": "Green Valley Apartments",
    "price": 7500000.0,
    "bedrooms": 3,
    "bathrooms": 2,
    "area_sqft": 1100.0,
    "property_type": "Apartment",
    "address": "Baner, Pune",
    "cover_image": None,
    "location": {"lat": 18.56, "lng": 73.78},
    "score": 82.5,
    "normal_score": 82.5,
    "budget_score": 88.0,
    "bedroom_score": 100.0,
    "area_score": 80.0,
    "location_score": 75.0,
    "location_rating": "Good Connectivity",
    "dimension_scores": {},
    "weights": {},
    "reasons": [],
}

FIXTURE_PREFERENCES = {
    "max_price": 8000000,
    "bedrooms": 3,
    "target_area_sqft": 1000,
}


class TestRecommendationExplainer:
    def setup_method(self):
        self.explainer = RecommendationExplainer()

    def test_explain_adds_match_tier(self):
        enriched = self.explainer.explain(FIXTURE_RESULT, FIXTURE_PREFERENCES)
        assert "match_tier" in enriched
        assert enriched["match_tier"] == MATCH_TIER_STRONG  # score=82.5 → Strong

    def test_explain_adds_match_summary(self):
        enriched = self.explainer.explain(FIXTURE_RESULT, FIXTURE_PREFERENCES)
        assert "match_summary" in enriched
        assert isinstance(enriched["match_summary"], str)
        assert len(enriched["match_summary"]) > 10

    def test_explain_adds_highlights(self):
        enriched = self.explainer.explain(FIXTURE_RESULT, FIXTURE_PREFERENCES)
        assert "highlights" in enriched
        assert isinstance(enriched["highlights"], list)

    def test_explain_adds_warnings(self):
        enriched = self.explainer.explain(FIXTURE_RESULT, FIXTURE_PREFERENCES)
        assert "warnings" in enriched
        assert isinstance(enriched["warnings"], list)

    def test_explain_adds_dimension_explanations(self):
        enriched = self.explainer.explain(FIXTURE_RESULT, FIXTURE_PREFERENCES)
        expl = enriched["dimension_explanations"]
        assert "budget" in expl
        assert "bedroom" in expl
        assert "area" in expl
        assert "location" in expl

    def test_explain_budget_is_excellent(self):
        enriched = self.explainer.explain(FIXTURE_RESULT, FIXTURE_PREFERENCES)
        assert enriched["dimension_explanations"]["budget"]["verdict"] == VERDICT_EXCELLENT

    def test_explain_bedroom_is_excellent(self):
        enriched = self.explainer.explain(FIXTURE_RESULT, FIXTURE_PREFERENCES)
        assert enriched["dimension_explanations"]["bedroom"]["verdict"] == VERDICT_EXCELLENT

    def test_explain_preserves_original_fields(self):
        enriched = self.explainer.explain(FIXTURE_RESULT, FIXTURE_PREFERENCES)
        assert enriched["property_id"] == 101
        assert enriched["title"] == "Green Valley Apartments"
        assert enriched["score"] == 82.5

    def test_explain_all_enriches_list(self):
        results = [FIXTURE_RESULT, {**FIXTURE_RESULT, "property_id": 102, "score": 55.0, "budget_score": 50.0}]
        enriched_list = self.explainer.explain_all(results, FIXTURE_PREFERENCES)
        assert len(enriched_list) == 2
        for item in enriched_list:
            assert "match_tier" in item
            assert "dimension_explanations" in item

    def test_explain_all_with_location_breakdown(self):
        breakdown = {
            101: {"Transport": {"score": 90}, "Healthcare": {"score": 40}},
        }
        enriched_list = self.explainer.explain_all(
            [FIXTURE_RESULT], FIXTURE_PREFERENCES, location_breakdowns=breakdown
        )
        loc_expl = enriched_list[0]["dimension_explanations"]["location"]
        assert any("Transport" in p for p in loc_expl["strong_pillars"])
        assert any("Healthcare" in p for p in loc_expl["weak_pillars"])

    def test_weak_match_property(self):
        weak_result = {**FIXTURE_RESULT, "score": 30.0, "budget_score": 10.0, "bedroom_score": 30.0,
                       "area_score": 30.0, "location_score": 30.0}
        enriched = self.explainer.explain(weak_result, FIXTURE_PREFERENCES)
        assert enriched["match_tier"] == MATCH_TIER_WEAK
        assert len(enriched["warnings"]) > 0

    def test_prime_match_property(self):
        prime_result = {**FIXTURE_RESULT, "score": 92.0, "budget_score": 95.0, "bedroom_score": 100.0,
                        "area_score": 92.0, "location_score": 90.0}
        enriched = self.explainer.explain(prime_result, FIXTURE_PREFERENCES)
        assert enriched["match_tier"] == MATCH_TIER_PRIME
        assert len(enriched["highlights"]) > 0

"""
Part 6.5 – Automated Test Suite for Recommendations (Deterministic Scoring)

Tests the complete recommendation scoring pipeline with fixed fixture inputs
and exact expected score values. No database required — all tests are pure.

Coverage:
A. score_budget_fit() — all scoring branches with exact expected values
B. score_bedroom_fit() — exact match, surplus, deficit cases
C. score_area_fit() — target mode, minimum mode, no-data fallback
D. normalize_dimension_weights() — normalisation arithmetic
E. format_inr_short() — INR formatting edge cases
F. RuleBasedRecommendation.recommend() — deterministic composite score
   using MockProperty objects (no DB), including:
   - Score ordering invariants
   - Custom weights shift ranking
   - Explanation enrichment present on every result
   - Hard-budget filtering not performed at strategy level (that's the view)
G. Score reproducibility — same inputs always produce identical outputs
H. Edge cases — zero budget, zero bedroom, missing area, large overage
"""

import pytest

from apps.recommendations.strategies import (
    score_budget_fit,
    score_bedroom_fit,
    score_area_fit,
    normalize_dimension_weights,
    format_inr_short,
    DEFAULT_PREFERENCE_WEIGHTS,
    DIMENSION_BUDGET,
    DIMENSION_BEDROOM,
    DIMENSION_AREA,
    DIMENSION_LOCATION,
    ALL_DIMENSIONS,
)


# ─── Shared mock property builder ─────────────────────────────────────────────

class MockProperty:
    """
    Lightweight property stub for deterministic strategy tests (no DB).
    Matches the attribute access pattern in RuleBasedRecommendation.recommend().
    """
    _image_queryset = None  # used for hasattr checks

    def __init__(
        self,
        id,
        title,
        price,
        bedrooms,
        area_sqft=0.0,
        property_type="Apartment",
        address="Test Address",
        latitude=22.58,
        longitude=88.42,
        bathrooms=2,
        status="Active",
        images=None,
    ):
        self.id = id
        self.title = title
        self.price = price
        self.bedrooms = bedrooms
        self.area_sqft = area_sqft
        self.property_type = property_type
        self.address = address
        self.latitude = latitude
        self.longitude = longitude
        self.bathrooms = bathrooms
        self.status = status
        self.cover_image = None
        # simulate property.images.exists() → False
        self.images = _EmptyImageSet()


class _EmptyImageSet:
    def exists(self):
        return False


# ─── Shared fixtures ───────────────────────────────────────────────────────────

@pytest.fixture
def prop_exact_match():
    """3BHK, 75L, 1450 sqft — designed as an ideal 3BHK/80L buyer match."""
    return MockProperty(id=1, title="Ideal 3BHK", price=7500000.0, bedrooms=3, area_sqft=1450.0)


@pytest.fixture
def prop_over_budget():
    """4BHK, 1.6Cr — exceeds 80L ceiling."""
    return MockProperty(id=2, title="Luxury 4BHK", price=16000000.0, bedrooms=4, area_sqft=2800.0)


@pytest.fixture
def prop_budget_2bhk():
    """2BHK, 45L, 900 sqft — under budget, wrong bedroom count."""
    return MockProperty(id=3, title="Starter 2BHK", price=4500000.0, bedrooms=2, area_sqft=900.0)


@pytest.fixture
def prop_no_area():
    """3BHK, 60L — no area data."""
    return MockProperty(id=4, title="No-Area 3BHK", price=6000000.0, bedrooms=3, area_sqft=0.0)


@pytest.fixture
def standard_preferences():
    return {
        "max_price": 8000000,        # 80L
        "target_price": 6500000,     # 65L target
        "bedrooms": 3,
        "target_area_sqft": 1400,
        "min_area_sqft": 900,
    }


# ==============================================================================
# A. score_budget_fit() — deterministic branch coverage
# ==============================================================================

class TestScoreBudgetFit:

    # ── With target + max range ──

    def test_below_target_scores_90_to_100(self):
        # Price 50L, target 60L, max 80L → in optimal zone
        score = score_budget_fit(price=5000000, max_budget=8000000, target_budget=6000000)
        assert 90.0 <= score <= 100.0

    def test_at_target_scores_90(self):
        # Price exactly at target → 90.0 (no surplus)
        score = score_budget_fit(price=6000000, max_budget=8000000, target_budget=6000000)
        assert score == 90.0

    def test_between_target_and_max_scores_50_to_90(self):
        # Price 75L, target 60L, max 80L → acceptable zone [50, 90)
        score = score_budget_fit(price=7500000, max_budget=8000000, target_budget=6000000)
        assert 50.0 <= score < 90.0

    def test_at_max_budget_with_target_scores_50(self):
        # Price exactly at max → 90 - 40 = 50.0
        score = score_budget_fit(price=8000000, max_budget=8000000, target_budget=6000000)
        assert score == 50.0

    def test_over_max_with_target_decay(self):
        # Over by 25% → penalty applied
        score = score_budget_fit(price=10000000, max_budget=8000000, target_budget=6000000)
        assert score < 50.0

    def test_far_over_budget_approaches_zero(self):
        score = score_budget_fit(price=30000000, max_budget=8000000, target_budget=6000000)
        assert score == 0.0

    # ── Without target (max-only mode) ──

    def test_max_only_under_ceiling(self):
        # Price 70L, max 80L → 100 - (70/80)*20 = 82.5
        score = score_budget_fit(price=7000000, max_budget=8000000)
        assert score == 82.5

    def test_max_only_well_under_ceiling(self):
        # Price 20L, max 80L → 100 - (20/80)*20 = 95.0
        score = score_budget_fit(price=2000000, max_budget=8000000)
        assert score == 95.0

    def test_max_only_at_ceiling(self):
        # Price = max → 80.0
        score = score_budget_fit(price=8000000, max_budget=8000000)
        assert score == 80.0

    def test_max_only_over_ceiling(self):
        # Over ceiling → decay below 80
        score = score_budget_fit(price=9000000, max_budget=8000000)
        assert score < 80.0
        assert score >= 0.0

    def test_no_budget_set_returns_default(self):
        # No budget → 85.0 fallback
        score = score_budget_fit(price=5000000, max_budget=0)
        assert score == 85.0

    def test_score_is_float(self):
        score = score_budget_fit(price=7500000, max_budget=8000000)
        assert isinstance(score, float)

    def test_score_never_negative(self):
        score = score_budget_fit(price=100000000, max_budget=5000000)
        assert score >= 0.0

    def test_score_never_exceeds_100(self):
        score = score_budget_fit(price=100000, max_budget=8000000, target_budget=6000000)
        assert score <= 100.0


# ==============================================================================
# B. score_bedroom_fit() — exact match, surplus, deficit
# ==============================================================================

class TestScoreBedroomFit:

    def test_exact_match_is_100(self):
        assert score_bedroom_fit(actual_bhk=1, desired_bhk=1) == 100.0
        assert score_bedroom_fit(actual_bhk=2, desired_bhk=2) == 100.0
        assert score_bedroom_fit(actual_bhk=3, desired_bhk=3) == 100.0
        assert score_bedroom_fit(actual_bhk=5, desired_bhk=5) == 100.0

    def test_plus_one_scores_85(self):
        assert score_bedroom_fit(actual_bhk=4, desired_bhk=3) == 85.0
        assert score_bedroom_fit(actual_bhk=3, desired_bhk=2) == 85.0

    def test_minus_one_scores_60(self):
        assert score_bedroom_fit(actual_bhk=2, desired_bhk=3) == 60.0
        assert score_bedroom_fit(actual_bhk=1, desired_bhk=2) == 60.0

    def test_minus_two_decays_significantly(self):
        score = score_bedroom_fit(actual_bhk=1, desired_bhk=3)
        assert 10.0 <= score < 60.0

    def test_large_deficit_floors_at_10(self):
        score = score_bedroom_fit(actual_bhk=1, desired_bhk=10)
        assert score == 10.0

    def test_large_surplus_floors_at_10(self):
        # + 5 rooms → 100 - (5 * 35) = -75 → clamped to 10
        score = score_bedroom_fit(actual_bhk=10, desired_bhk=5)
        assert score == 10.0

    def test_plus_two_decays_from_85(self):
        score = score_bedroom_fit(actual_bhk=5, desired_bhk=3)
        assert 10.0 <= score < 85.0

    def test_score_never_negative(self):
        assert score_bedroom_fit(actual_bhk=1, desired_bhk=20) >= 0.0

    def test_score_never_exceeds_100(self):
        assert score_bedroom_fit(actual_bhk=5, desired_bhk=1) <= 100.0


# ==============================================================================
# C. score_area_fit() — all branches
# ==============================================================================

class TestScoreAreaFit:

    # ── Target mode ──

    def test_at_target_scores_90(self):
        score = score_area_fit(actual_sqft=1400, target_sqft=1400)
        assert score == 90.0

    def test_above_target_up_to_100(self):
        score = score_area_fit(actual_sqft=1600, target_sqft=1400)
        assert 90.0 < score <= 100.0

    def test_well_above_target_caps_at_100(self):
        # Very large surplus → capped at 100
        score = score_area_fit(actual_sqft=10000, target_sqft=1400)
        assert score == 100.0

    def test_below_target_decays(self):
        score = score_area_fit(actual_sqft=1000, target_sqft=1400)
        assert score < 90.0

    def test_far_below_target_floors_at_20(self):
        # deficit large enough: sqft=1, target=1400 → deficit≈1.0 → 90-(1.0*70)=20 → floored at 20
        # actual: (1400-1)/1400=0.99929 → 90-(0.99929*70)=90-69.95=20.05 (just above floor)
        score = score_area_fit(actual_sqft=1, target_sqft=1400)
        assert 20.0 <= score <= 21.0

    # ── Minimum mode ──

    def test_meets_minimum_is_100(self):
        assert score_area_fit(actual_sqft=1000, min_sqft=900) == 100.0
        assert score_area_fit(actual_sqft=900, min_sqft=900) == 100.0

    def test_below_minimum_decays(self):
        score = score_area_fit(actual_sqft=700, min_sqft=900)
        assert score < 100.0
        assert score >= 20.0

    def test_far_below_minimum_floors_at_20(self):
        # sqft=1, min=10000 → deficit=9999/10000=0.9999 → 100-(0.9999*80)=20.008 (just above floor 20)
        score = score_area_fit(actual_sqft=1, min_sqft=10000)
        assert 20.0 <= score <= 21.0

    # ── No-data fallback ──

    def test_zero_area_no_target_returns_80(self):
        # actual_sqft=0, no target → 80.0
        score = score_area_fit(actual_sqft=0.0, target_sqft=0, min_sqft=0)
        assert score == 80.0

    def test_no_target_no_min_returns_85(self):
        # actual_sqft > 0, no target, no min → 85.0
        score = score_area_fit(actual_sqft=1200, target_sqft=0, min_sqft=0)
        assert score == 85.0

    def test_score_always_within_bounds(self):
        for sqft in [0, 50, 200, 900, 1400, 5000]:
            s = score_area_fit(actual_sqft=sqft, target_sqft=1200)
            assert 0.0 <= s <= 100.0, f"Out of bounds for sqft={sqft}: {s}"


# ==============================================================================
# D. normalize_dimension_weights() — arithmetic correctness
# ==============================================================================

class TestNormalizeDimensionWeights:

    def test_defaults_when_none(self):
        result = normalize_dimension_weights(None)
        assert result == DEFAULT_PREFERENCE_WEIGHTS

    def test_defaults_when_empty(self):
        result = normalize_dimension_weights({})
        assert result == DEFAULT_PREFERENCE_WEIGHTS

    def test_normalisation_sums_to_one(self):
        custom = {"budget": 3.0, "bedroom": 1.0, "area": 1.0, "location": 1.0}
        result = normalize_dimension_weights(custom)
        assert abs(sum(result.values()) - 1.0) < 1e-4

    def test_exact_normalisation_values(self):
        custom = {"budget": 2.0, "bedroom": 1.0, "area": 0.5, "location": 0.5}
        result = normalize_dimension_weights(custom)
        assert result[DIMENSION_BUDGET] == 0.5
        assert result[DIMENSION_BEDROOM] == 0.25
        assert result[DIMENSION_AREA] == 0.125
        assert result[DIMENSION_LOCATION] == 0.125

    def test_all_equal_weights_normalise_to_quarter(self):
        custom = {"budget": 1, "bedroom": 1, "area": 1, "location": 1}
        result = normalize_dimension_weights(custom)
        for dim in ALL_DIMENSIONS:
            assert result[dim] == 0.25

    def test_single_dimension_100_percent(self):
        custom = {"budget": 0, "bedroom": 0, "area": 0, "location": 1}
        result = normalize_dimension_weights(custom)
        assert result[DIMENSION_LOCATION] == 1.0
        assert result[DIMENSION_BUDGET] == 0.0

    def test_all_zeros_falls_back_to_defaults(self):
        custom = {"budget": 0, "bedroom": 0, "area": 0, "location": 0}
        result = normalize_dimension_weights(custom)
        assert result == DEFAULT_PREFERENCE_WEIGHTS

    def test_all_dimensions_present_in_result(self):
        result = normalize_dimension_weights({"budget": 2, "bedroom": 1})
        for dim in ALL_DIMENSIONS:
            assert dim in result

    def test_negative_values_clamped_to_zero(self):
        custom = {"budget": -5, "bedroom": 2, "area": 1, "location": 1}
        result = normalize_dimension_weights(custom)
        # Negative budget clamped → budget gets 0%
        assert result[DIMENSION_BUDGET] == 0.0
        assert abs(sum(result.values()) - 1.0) < 1e-6

    def test_invalid_type_falls_back_to_default(self):
        custom = {"budget": "notanumber", "bedroom": 1, "area": 1, "location": 1}
        result = normalize_dimension_weights(custom)
        # Should not crash; budget falls back to default value
        assert result is not None
        assert abs(sum(result.values()) - 1.0) < 1e-6


# ==============================================================================
# E. format_inr_short() — INR formatting
# ==============================================================================

class TestFormatInrShort:

    def test_crore_format(self):
        assert format_inr_short(10000000) == "₹1.00 Cr"
        assert format_inr_short(16000000) == "₹1.60 Cr"
        assert format_inr_short(25000000) == "₹2.50 Cr"

    def test_lakh_format(self):
        assert format_inr_short(7500000) == "₹75.00 L"
        assert format_inr_short(4500000) == "₹45.00 L"
        assert format_inr_short(100000) == "₹1.00 L"

    def test_below_lakh_format(self):
        result = format_inr_short(50000)
        assert result == "₹50,000"

    def test_boundary_exactly_one_crore(self):
        assert format_inr_short(10000000) == "₹1.00 Cr"

    def test_boundary_exactly_one_lakh(self):
        assert format_inr_short(100000) == "₹1.00 L"


# ==============================================================================
# F. RuleBasedRecommendation — deterministic composite score (no DB)
# ==============================================================================

class TestRuleBasedRecommendationDeterministic:
    """
    Uses MockProperty to bypass the database entirely.
    Patches AmenitySpatialService at the strategies module level using monkeypatch
    to avoid triggering the GDAL import chain in apps.amenities.services.
    """

    def _patch_location(self, monkeypatch, score=80.0, rating="Standard"):
        """Patch RuleBasedRecommendation's inline import of AmenitySpatialService."""
        class _FakeSvc:
            @staticmethod
            def calculate_location_score_for_property(prop, custom_weights=None):
                return {"composite_score": score, "rating": rating, "pillars": {}}

        # Patch inside the strategies module's namespace (where it's imported inline)
        import apps.recommendations.strategies as strat_mod
        import sys

        # Create a fake amenities.services module if it hasn't been imported yet
        import types
        fake_svc_mod = types.ModuleType("apps.amenities.services")
        fake_svc_mod.AmenitySpatialService = _FakeSvc
        monkeypatch.setitem(sys.modules, "apps.amenities.services", fake_svc_mod)

    def test_three_candidates_correct_ranking(self, monkeypatch, prop_exact_match, prop_over_budget, prop_budget_2bhk):
        self._patch_location(monkeypatch)
        from apps.recommendations.strategies import RuleBasedRecommendation

        strategy = RuleBasedRecommendation()
        prefs = {"max_price": 8000000, "bedrooms": 3, "target_area_sqft": 1400}
        results = strategy.recommend([prop_exact_match, prop_over_budget, prop_budget_2bhk], prefs)

        assert len(results) == 3
        assert results[0]["property_id"] == prop_exact_match.id
        assert results[0]["score"] >= results[1]["score"] >= results[2]["score"]

    def test_exact_bedroom_match_scores_100(self, monkeypatch, prop_exact_match):
        self._patch_location(monkeypatch)
        from apps.recommendations.strategies import RuleBasedRecommendation

        strategy = RuleBasedRecommendation()
        results = strategy.recommend([prop_exact_match], {"bedrooms": 3})
        assert results[0]["bedroom_score"] == 100.0

    def test_budget_score_below_ceiling(self, monkeypatch, prop_exact_match):
        self._patch_location(monkeypatch)
        from apps.recommendations.strategies import RuleBasedRecommendation

        strategy = RuleBasedRecommendation()
        results = strategy.recommend([prop_exact_match], {"max_price": 8000000, "bedrooms": 3})
        assert results[0]["budget_score"] > 80.0

    def test_custom_weights_shift_ranking(self, monkeypatch, prop_exact_match, prop_over_budget, prop_budget_2bhk):
        """With 100% bedroom weight, the 4BHK property ranks #1 for a 4BHK buyer."""
        self._patch_location(monkeypatch)
        from apps.recommendations.strategies import RuleBasedRecommendation

        strategy = RuleBasedRecommendation()
        prefs = {
            "bedrooms": 4,
            "weights": {"budget": 0, "bedroom": 1, "area": 0, "location": 0}
        }
        results = strategy.recommend([prop_exact_match, prop_over_budget, prop_budget_2bhk], prefs)
        assert results[0]["property_id"] == prop_over_budget.id
        assert results[0]["bedroom_score"] == 100.0

    def test_result_keys_present(self, monkeypatch, prop_exact_match):
        self._patch_location(monkeypatch)
        from apps.recommendations.strategies import RuleBasedRecommendation

        strategy = RuleBasedRecommendation()
        results = strategy.recommend([prop_exact_match], {"bedrooms": 3})
        r = results[0]
        required_keys = [
            "property_id", "title", "price", "bedrooms", "area_sqft",
            "score", "budget_score", "bedroom_score", "area_score",
            "location_score", "dimension_scores", "reasons",
            # Part 6.3 enrichment
            "match_tier", "match_summary", "highlights", "warnings",
            "dimension_explanations",
        ]
        for key in required_keys:
            assert key in r, f"Missing key: {key}"

    def test_explanation_enrichment_present(self, monkeypatch, prop_exact_match):
        """Every result must include Part 6.3 explanation fields."""
        self._patch_location(monkeypatch, score=90.0, rating="Prime Connectivity")
        from apps.recommendations.strategies import RuleBasedRecommendation

        strategy = RuleBasedRecommendation()
        results = strategy.recommend([prop_exact_match], {"bedrooms": 3, "max_price": 8000000})
        r = results[0]
        assert "match_tier" in r
        assert "match_summary" in r
        assert isinstance(r["highlights"], list)
        assert isinstance(r["warnings"], list)
        expl = r["dimension_explanations"]
        for dim in ("budget", "bedroom", "area", "location"):
            assert dim in expl
            assert "verdict" in expl[dim]
            assert "narrative" in expl[dim]

    def test_score_ordering_is_descending(self, monkeypatch, prop_exact_match, prop_over_budget, prop_budget_2bhk):
        self._patch_location(monkeypatch)
        from apps.recommendations.strategies import RuleBasedRecommendation

        strategy = RuleBasedRecommendation()
        prefs = {"bedrooms": 3, "max_price": 8000000}
        results = strategy.recommend([prop_exact_match, prop_over_budget, prop_budget_2bhk], prefs)
        scores = [r["score"] for r in results]
        assert scores == sorted(scores, reverse=True), f"Not descending: {scores}"

    def test_score_reproducibility(self, monkeypatch, prop_exact_match):
        """Same inputs → identical scores on two consecutive calls."""
        self._patch_location(monkeypatch)
        from apps.recommendations.strategies import RuleBasedRecommendation

        strategy = RuleBasedRecommendation()
        prefs = {"bedrooms": 3, "max_price": 8000000, "target_area_sqft": 1400}
        r1 = strategy.recommend([prop_exact_match], prefs)[0]["score"]
        r2 = strategy.recommend([prop_exact_match], prefs)[0]["score"]
        assert r1 == r2





# ==============================================================================
# G. Edge Cases
# ==============================================================================

class TestEdgeCases:

    def test_budget_fit_zero_max_returns_default(self):
        score = score_budget_fit(price=5000000, max_budget=0)
        assert score == 85.0

    def test_bedroom_fit_zero_desired_uses_one(self):
        # desired=0 is invalid — function defaults to desired=1 via caller
        # but underlying function should not crash
        score = score_bedroom_fit(actual_bhk=1, desired_bhk=0)
        # actual=1, desired=0 → diff=+1 → 85.0
        assert score == 85.0

    def test_area_fit_negative_actual(self):
        # Negative area treated as missing → 80.0 fallback
        score = score_area_fit(actual_sqft=-100, target_sqft=1200)
        assert score == 80.0

    def test_normalize_weights_case_insensitive_keys(self):
        custom = {"Budget": 2.0, "BEDROOM": 1.0, "area": 0.5, "Location": 0.5}
        result = normalize_dimension_weights(custom)
        assert abs(sum(result.values()) - 1.0) < 1e-6

    def test_budget_score_target_equals_max(self):
        # target == max → any price at target/max → should not crash
        score = score_budget_fit(price=8000000, max_budget=8000000, target_budget=8000000)
        assert 0.0 <= score <= 100.0

    def test_area_fit_target_zero_with_min_zero(self):
        # No targets → positive sqft → 85.0
        score = score_area_fit(actual_sqft=1000, target_sqft=0, min_sqft=0)
        assert score == 85.0

    def test_normalize_weights_with_single_key(self):
        # Only budget provided → others get default values, then normalised
        result = normalize_dimension_weights({"budget": 3.0})
        assert abs(sum(result.values()) - 1.0) < 1e-6
        assert result[DIMENSION_BUDGET] > result[DIMENSION_AREA]

    def test_format_inr_zero(self):
        result = format_inr_short(0)
        assert result == "₹0"

    def test_bedroom_fit_same_large_number(self):
        assert score_bedroom_fit(actual_bhk=10, desired_bhk=10) == 100.0

    def test_budget_extremely_large_price_clamps_to_zero(self):
        score = score_budget_fit(price=999_999_999, max_budget=5000000)
        assert score == 0.0

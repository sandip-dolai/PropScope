"""
Recommendation Explanation Generator (Part 6.3)

Transforms raw dimension scores and property data into structured, human-readable
explanation objects for each property recommendation:
- Match tier classification (Prime Match, Strong Match, Good Match, Fair Match, Weak Match)
- Per-dimension verdict codes (EXCELLENT / GOOD / FAIR / POOR) with narrative labels
- Positive highlights and trade-off warnings
- One-sentence natural-language summary for UI display
"""

# Match tier thresholds (based on composite score 0 - 100)
MATCH_TIER_PRIME = "Prime Match"        # ≥88
MATCH_TIER_STRONG = "Strong Match"     # ≥74
MATCH_TIER_GOOD = "Good Match"         # ≥60
MATCH_TIER_FAIR = "Fair Match"         # ≥45
MATCH_TIER_WEAK = "Weak Match"         # < 45

# Verdict codes for each dimension
VERDICT_EXCELLENT = "EXCELLENT"
VERDICT_GOOD = "GOOD"
VERDICT_FAIR = "FAIR"
VERDICT_POOR = "POOR"


def classify_match_tier(composite_score: float) -> str:
    """Returns a human-readable match tier for a composite score (0-100)."""
    if composite_score >= 88.0:
        return MATCH_TIER_PRIME
    elif composite_score >= 74.0:
        return MATCH_TIER_STRONG
    elif composite_score >= 60.0:
        return MATCH_TIER_GOOD
    elif composite_score >= 45.0:
        return MATCH_TIER_FAIR
    return MATCH_TIER_WEAK


def verdict_code(score: float) -> str:
    """Maps a dimension score (0-100) to a verdict code."""
    if score >= 85.0:
        return VERDICT_EXCELLENT
    elif score >= 65.0:
        return VERDICT_GOOD
    elif score >= 45.0:
        return VERDICT_FAIR
    return VERDICT_POOR


def generate_budget_explanation(
    price: float,
    max_budget: float,
    target_budget: float,
    budget_score: float,
    format_fn,
) -> dict:
    """Generates structured budget dimension explanation."""
    code = verdict_code(budget_score)

    if code == VERDICT_EXCELLENT:
        narrative = f"Well within your budget at {format_fn(price)} (ceiling {format_fn(max_budget)})"
        highlight = True
        warning = None
    elif code == VERDICT_GOOD:
        narrative = f"Comfortably within your budget at {format_fn(price)} of {format_fn(max_budget)}"
        highlight = True
        warning = None
    elif code == VERDICT_FAIR:
        if price > max_budget:
            overage_pct = round((price - max_budget) / max_budget * 100, 1)
            narrative = f"Slightly over budget by {overage_pct}% ({format_fn(price)} vs {format_fn(max_budget)})"
            highlight = False
            warning = f"Priced {overage_pct}% above your ceiling"
        else:
            narrative = f"At the upper end of your budget ({format_fn(price)} of {format_fn(max_budget)})"
            highlight = False
            warning = "Close to your budget ceiling"
    else:
        overage_pct = round((price - max_budget) / max_budget * 100, 1) if price > max_budget else 0
        narrative = f"Significantly over budget ({format_fn(price)} vs {format_fn(max_budget)})"
        highlight = False
        warning = f"Exceeds your budget ceiling by {overage_pct}%"

    return {
        "dimension": "budget",
        "verdict": code,
        "score": round(budget_score, 1),
        "narrative": narrative,
        "is_highlight": highlight,
        "warning": warning,
    }


def generate_bedroom_explanation(
    actual_bhk: int,
    desired_bhk: int,
    bedroom_score: float,
) -> dict:
    """Generates structured bedroom dimension explanation."""
    code = verdict_code(bedroom_score)
    diff = actual_bhk - desired_bhk

    if diff == 0:
        narrative = f"Exactly {actual_bhk} BHK as you requested"
        highlight = True
        warning = None
    elif diff > 0:
        extra = "rooms" if diff > 1 else "room"
        narrative = f"{actual_bhk} BHK — {diff} extra {extra} beyond your preference"
        highlight = True
        warning = None
    else:
        deficit = abs(diff)
        rooms = "rooms" if deficit > 1 else "room"
        narrative = f"{actual_bhk} BHK — {deficit} {rooms} fewer than your {desired_bhk} BHK preference"
        highlight = False
        warning = f"{deficit} BHK short of your requirement"

    return {
        "dimension": "bedroom",
        "verdict": code,
        "score": round(bedroom_score, 1),
        "narrative": narrative,
        "is_highlight": highlight,
        "warning": warning,
    }


def generate_area_explanation(
    actual_sqft: float,
    target_sqft: float,
    min_sqft: float,
    area_score: float,
) -> dict:
    """Generates structured area / size dimension explanation."""
    code = verdict_code(area_score)

    if actual_sqft <= 0:
        narrative = "Area information not available"
        highlight = False
        warning = None
    elif target_sqft > 0:
        if actual_sqft >= target_sqft:
            surplus_pct = round((actual_sqft - target_sqft) / target_sqft * 100, 1)
            narrative = f"{int(actual_sqft)} sqft — {surplus_pct}% more than your target {int(target_sqft)} sqft"
            highlight = True
            warning = None
        else:
            deficit_pct = round((target_sqft - actual_sqft) / target_sqft * 100, 1)
            narrative = f"{int(actual_sqft)} sqft — {deficit_pct}% smaller than your ideal {int(target_sqft)} sqft"
            highlight = code in (VERDICT_EXCELLENT, VERDICT_GOOD)
            warning = f"{deficit_pct}% below your target size" if code in (VERDICT_FAIR, VERDICT_POOR) else None
    elif min_sqft > 0:
        if actual_sqft >= min_sqft:
            narrative = f"{int(actual_sqft)} sqft — meets your minimum requirement of {int(min_sqft)} sqft"
            highlight = True
            warning = None
        else:
            deficit = int(min_sqft - actual_sqft)
            narrative = f"{int(actual_sqft)} sqft — {deficit} sqft below your minimum of {int(min_sqft)} sqft"
            highlight = False
            warning = f"{deficit} sqft short of minimum"
    else:
        narrative = f"{int(actual_sqft)} sqft living area"
        highlight = code == VERDICT_EXCELLENT
        warning = None

    return {
        "dimension": "area",
        "verdict": code,
        "score": round(area_score, 1),
        "narrative": narrative,
        "is_highlight": highlight,
        "warning": warning,
    }


def generate_location_explanation(
    location_score: float,
    location_rating: str,
    location_breakdown: dict = None,
) -> dict:
    """Generates structured location dimension explanation."""
    code = verdict_code(location_score)

    if code == VERDICT_EXCELLENT:
        narrative = f"Outstanding location connectivity ({location_rating}, {location_score}%)"
        highlight = True
        warning = None
    elif code == VERDICT_GOOD:
        narrative = f"Good spatial connectivity ({location_rating}, {location_score}%)"
        highlight = True
        warning = None
    elif code == VERDICT_FAIR:
        narrative = f"Moderate accessibility to key amenities ({location_rating}, {location_score}%)"
        highlight = False
        warning = "Some amenities may require longer commutes"
    else:
        narrative = f"Limited nearby amenity access ({location_rating}, {location_score}%)"
        highlight = False
        warning = "Low proximity to key lifestyle amenities"

    # Surface weakest pillars for trade-off info
    weak_pillars = []
    strong_pillars = []
    if location_breakdown:
        for pillar_name, pillar_info in location_breakdown.items():
            pillar_score = pillar_info.get("score", 0)
            if pillar_score < 50:
                weak_pillars.append(f"{pillar_name} ({pillar_score}%)")
            elif pillar_score >= 85:
                strong_pillars.append(f"{pillar_name} ({pillar_score}%)")

    return {
        "dimension": "location",
        "verdict": code,
        "score": round(location_score, 1),
        "narrative": narrative,
        "is_highlight": highlight,
        "warning": warning,
        "strong_pillars": strong_pillars,
        "weak_pillars": weak_pillars,
    }


def generate_match_summary(
    match_tier: str,
    title: str,
    composite_score: float,
    highlights: list,
    warnings: list,
    desired_bhk: int,
    max_budget: float,
    format_fn,
) -> str:
    """
    Generates a concise one-sentence natural-language summary for display in UI cards.
    """
    if match_tier == MATCH_TIER_PRIME:
        prefix = "Exceptional match"
    elif match_tier == MATCH_TIER_STRONG:
        prefix = "Strong match"
    elif match_tier == MATCH_TIER_GOOD:
        prefix = "Good match"
    elif match_tier == MATCH_TIER_FAIR:
        prefix = "Partial match"
    else:
        prefix = "Weak match"

    # Base summary
    summary = f"{prefix} ({round(composite_score, 1)}%) for a {desired_bhk} BHK within {format_fn(max_budget)}"

    if highlights:
        summary += f" — {highlights[0].lower()}"

    if warnings:
        summary += f". Note: {warnings[0].lower()}"

    return summary


class RecommendationExplainer:
    """
    Generates structured, human-readable explanation objects for ranked property matches.
    Enriches each recommendation result with:
    - Match tier (Prime / Strong / Good / Fair / Weak)
    - Dimension-level verdicts with narrative, highlights, and warnings
    - Match summary sentence
    - Consolidated highlights and trade-off list
    """

    def __init__(self, format_fn=None):
        self.format_fn = format_fn or self._default_format

    @staticmethod
    def _default_format(amount: float) -> str:
        if amount >= 10000000:
            return f"₹{amount / 10000000:.2f} Cr"
        elif amount >= 100000:
            return f"₹{amount / 100000:.2f} L"
        return f"₹{int(amount):,}"

    def explain(
        self,
        result: dict,
        preferences: dict,
        location_breakdown: dict = None,
    ) -> dict:
        """
        Takes a scored recommendation result dict and enriches it with a full explanation.
        Returns the original result dict merged with explanation fields.
        """
        price = float(result.get("price", 0))
        actual_bhk = int(result.get("bedrooms", 1))
        actual_sqft = float(result.get("area_sqft", 0))
        composite_score = float(result.get("score", 0))
        budget_score = float(result.get("budget_score", 80.0))
        bedroom_score = float(result.get("bedroom_score", 80.0))
        area_score = float(result.get("area_score", 80.0))
        location_score = float(result.get("location_score", 80.0))
        location_rating = result.get("location_rating", "Standard Accessibility")

        max_budget = float(preferences.get("max_price", 0)) or float(preferences.get("max_budget", 0)) or 100000000.0
        target_budget = float(preferences.get("target_price", 0)) or float(preferences.get("target_budget", 0))
        desired_bedrooms = int(preferences.get("bedrooms", 1) or 1)
        target_sqft = float(preferences.get("target_area_sqft", 0) or preferences.get("area_sqft", 0))
        min_sqft = float(preferences.get("min_area_sqft", 0))

        # Match tier classification
        match_tier = classify_match_tier(composite_score)

        # Per-dimension structured explanations
        budget_expl = generate_budget_explanation(price, max_budget, target_budget, budget_score, self.format_fn)
        bedroom_expl = generate_bedroom_explanation(actual_bhk, desired_bedrooms, bedroom_score)
        area_expl = generate_area_explanation(actual_sqft, target_sqft, min_sqft, area_score)
        location_expl = generate_location_explanation(location_score, location_rating, location_breakdown)

        dimension_explanations = {
            "budget": budget_expl,
            "bedroom": bedroom_expl,
            "area": area_expl,
            "location": location_expl,
        }

        # Collect highlights (positive signals) and warnings (trade-offs)
        highlights = [
            d["narrative"]
            for d in dimension_explanations.values()
            if d.get("is_highlight")
        ]
        warnings = [
            d["warning"]
            for d in dimension_explanations.values()
            if d.get("warning")
        ]

        # Also surface strong / weak location pillars
        strong_loc = location_expl.get("strong_pillars", [])
        weak_loc = location_expl.get("weak_pillars", [])
        if strong_loc:
            highlights.append(f"Strong on: {', '.join(strong_loc)}")
        if weak_loc:
            warnings.append(f"Weak on: {', '.join(weak_loc)}")

        # Match summary sentence
        match_summary = generate_match_summary(
            match_tier=match_tier,
            title=result.get("title", ""),
            composite_score=composite_score,
            highlights=highlights,
            warnings=warnings,
            desired_bhk=desired_bedrooms,
            max_budget=max_budget,
            format_fn=self.format_fn,
        )

        return {
            **result,
            "match_tier": match_tier,
            "match_summary": match_summary,
            "highlights": highlights,
            "warnings": warnings,
            "dimension_explanations": dimension_explanations,
        }

    def explain_all(
        self,
        results: list,
        preferences: dict,
        location_breakdowns: dict = None,
    ) -> list:
        """
        Enriches a full ranked results list with explanation objects.
        location_breakdowns: optional dict of {property_id: breakdown_dict}
        """
        location_breakdowns = location_breakdowns or {}
        return [
            self.explain(
                result,
                preferences,
                location_breakdown=location_breakdowns.get(result.get("property_id")),
            )
            for result in results
        ]

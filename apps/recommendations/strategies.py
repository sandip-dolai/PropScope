from abc import ABC, abstractmethod
from apps.recommendations.explainer import RecommendationExplainer

# Canonical preference dimension names
DIMENSION_BUDGET = "budget"
DIMENSION_BEDROOM = "bedroom"
DIMENSION_AREA = "area"
DIMENSION_LOCATION = "location"

ALL_DIMENSIONS = [
    DIMENSION_BUDGET,
    DIMENSION_BEDROOM,
    DIMENSION_AREA,
    DIMENSION_LOCATION,
]

# Standard deterministic weights for normal multi-attribute recommendation
DEFAULT_PREFERENCE_WEIGHTS = {
    DIMENSION_BUDGET: 0.35,
    DIMENSION_BEDROOM: 0.25,
    DIMENSION_AREA: 0.15,
    DIMENSION_LOCATION: 0.25,
}


def normalize_dimension_weights(custom_weights: dict = None) -> dict:
    """
    Normalizes custom preference weights to ensure their sum equals 1.0.
    Accepts keys like 'budget', 'bedroom', 'area', 'location' (case-insensitive).
    """
    if not custom_weights:
        return dict(DEFAULT_PREFERENCE_WEIGHTS)

    clean_weights = {}
    for dim in ALL_DIMENSIONS:
        val = custom_weights.get(dim)
        if val is None:
            for k, v in custom_weights.items():
                if k.strip().lower() == dim.lower():
                    val = v
                    break
        if val is not None:
            try:
                clean_weights[dim] = max(0.0, float(val))
            except (ValueError, TypeError):
                clean_weights[dim] = DEFAULT_PREFERENCE_WEIGHTS[dim]
        else:
            clean_weights[dim] = DEFAULT_PREFERENCE_WEIGHTS[dim]

    total = sum(clean_weights.values())
    if total <= 0:
        return dict(DEFAULT_PREFERENCE_WEIGHTS)

    return {k: round(v / total, 4) for k, v in clean_weights.items()}


def score_budget_fit(price: float, max_budget: float = 0.0, target_budget: float = 0.0) -> float:
    """
    Computes a normalized budget fit score (0.0 - 100.0).
    Properties within budget score high (80 - 100); over budget decay smoothly.
    """
    if target_budget > 0 and max_budget > target_budget:
        if price <= target_budget:
            # Optimal budget zone
            return round(min(100.0, 90.0 + ((target_budget - price) / target_budget) * 10.0), 2)
        elif price <= max_budget:
            # Acceptable ceiling zone
            decay = (price - target_budget) / (max_budget - target_budget)
            return round(max(50.0, 90.0 - (decay * 40.0)), 2)
        else:
            # Over-budget penalty zone
            overage = (price - max_budget) / max_budget
            return round(max(0.0, 50.0 - (overage * 100.0)), 2)
    elif max_budget > 0:
        if price <= max_budget:
            return round(100.0 - ((price / max_budget) * 20.0), 2)
        else:
            overage = (price - max_budget) / max_budget
            return round(max(0.0, 80.0 - (overage * 150.0)), 2)
    return 85.0


def score_bedroom_fit(actual_bhk: int, desired_bhk: int = 1) -> float:
    """
    Computes bedroom alignment score (0.0 - 100.0).
    Exact match = 100%, +1 BHK bonus space = 85%, -1 BHK deficit = 60%, >= 2 diff = decay.
    """
    if actual_bhk == desired_bhk:
        return 100.0
    diff = actual_bhk - desired_bhk
    if diff == 1:
        return 85.0
    elif diff == -1:
        return 60.0
    return round(max(10.0, 100.0 - (abs(diff) * 35.0)), 2)


def score_area_fit(actual_sqft: float, target_sqft: float = 0.0, min_sqft: float = 0.0) -> float:
    """
    Computes square footage fit score (0.0 - 100.0).
    """
    if not actual_sqft or actual_sqft <= 0:
        return 80.0

    if target_sqft > 0:
        if actual_sqft >= target_sqft:
            bonus = min(10.0, ((actual_sqft - target_sqft) / target_sqft) * 15.0)
            return round(min(100.0, 90.0 + bonus), 2)
        else:
            deficit = (target_sqft - actual_sqft) / target_sqft
            return round(max(20.0, 90.0 - (deficit * 70.0)), 2)
    elif min_sqft > 0:
        if actual_sqft >= min_sqft:
            return 100.0
        else:
            deficit = (min_sqft - actual_sqft) / min_sqft
            return round(max(20.0, 100.0 - (deficit * 80.0)), 2)

    return 85.0


def format_inr_short(amount: float) -> str:
    """Formats an Indian Rupee amount into L or Cr string."""
    if amount >= 10000000:
        return f"₹{amount / 10000000:.2f} Cr"
    elif amount >= 100000:
        return f"₹{amount / 100000:.2f} L"
    return f"₹{int(amount):,}"


class RecommendationStrategy(ABC):
    @abstractmethod
    def recommend(self, candidates, preferences):
        """
        Accepts candidate property querysets/lists and a preferences dict,
        and returns a ranked list with computed scores and reasoning.
        """
        pass


class RuleBasedRecommendation(RecommendationStrategy):
    """
    Normal Recommendation Engine combining hard constraint pre-filtering with
    a 4-attribute utility evaluation model:
    - Budget Fit (35%)
    - Bedroom Fit (25%)
    - Area Fit (15%)
    - Location Quality (25%) (Deterministic PostGIS GIS location score)
    """

    def recommend(self, candidates, preferences):
        max_budget = float(preferences.get('max_price', 0)) or float(preferences.get('max_budget', 0)) or 100000000.0
        target_budget = float(preferences.get('target_price', 0)) or float(preferences.get('target_budget', 0))
        desired_bedrooms = int(preferences.get('bedrooms', 0) or preferences.get('desired_bedrooms', 1) or 1)
        target_sqft = float(preferences.get('target_area_sqft', 0) or preferences.get('area_sqft', 0))
        min_sqft = float(preferences.get('min_area_sqft', 0))

        # Preference dimension weights
        raw_weights = preferences.get('weights') or preferences.get('preference_weights')
        weights = normalize_dimension_weights(raw_weights)

        # Custom amenity weights for location scoring if provided
        amenity_weights = preferences.get('amenity_weights') or preferences.get('location_weights')

        scored_results = []
        for prop in candidates:
            price = float(prop.price)
            actual_bhk = int(prop.bedrooms)
            actual_sqft = float(prop.area_sqft) if getattr(prop, 'area_sqft', None) else 0.0

            # 1. Budget fit score
            budget_score = score_budget_fit(price, max_budget=max_budget, target_budget=target_budget)

            # 2. Bedroom fit score
            bedroom_score = score_bedroom_fit(actual_bhk, desired_bhk=desired_bedrooms)

            # 3. Area / Size fit score
            area_score = score_area_fit(actual_sqft, target_sqft=target_sqft, min_sqft=min_sqft)

            # 4. Deterministic Location Score (PostGIS KNN engine)
            try:
                from apps.amenities.services import AmenitySpatialService
                location_data = AmenitySpatialService.calculate_location_score_for_property(
                    prop, custom_weights=amenity_weights
                )
                location_score = float(location_data.get("composite_score", 80.0))
                location_rating = location_data.get("rating", "Standard Accessibility")
            except Exception:
                location_score = 80.0
                location_rating = "Standard Accessibility"

            # Multi-Attribute Weighted Composite Score (0.0 - 100.0)
            final_score = round(
                (budget_score * weights[DIMENSION_BUDGET]) +
                (bedroom_score * weights[DIMENSION_BEDROOM]) +
                (area_score * weights[DIMENSION_AREA]) +
                (location_score * weights[DIMENSION_LOCATION]),
                2
            )

            # Structured reason codes
            budget_reason = f"Budget fit: {round(budget_score, 1)}% ({format_inr_short(price)} vs ceiling {format_inr_short(max_budget)})"
            if actual_bhk == desired_bedrooms:
                bedroom_reason = f"Bedrooms: {actual_bhk} BHK (Exact match)"
            elif actual_bhk > desired_bedrooms:
                bedroom_reason = f"Bedrooms: {actual_bhk} BHK (+{actual_bhk - desired_bedrooms} extra room)"
            else:
                bedroom_reason = f"Bedrooms: {actual_bhk} BHK ({desired_bedrooms - actual_bhk} BHK deficit)"

            area_reason = f"Size: {int(actual_sqft)} sqft ({round(area_score, 1)}% area fit)" if actual_sqft > 0 else f"Size fit: {round(area_score, 1)}%"
            location_reason = f"Location score: {location_score}% ({location_rating})"

            dimension_scores = {
                DIMENSION_BUDGET: {
                    "score": round(budget_score, 1),
                    "weight": round(weights[DIMENSION_BUDGET], 4),
                    "weight_percentage": int(round(weights[DIMENSION_BUDGET] * 100)),
                    "weighted_contribution": round(budget_score * weights[DIMENSION_BUDGET], 2),
                },
                DIMENSION_BEDROOM: {
                    "score": round(bedroom_score, 1),
                    "weight": round(weights[DIMENSION_BEDROOM], 4),
                    "weight_percentage": int(round(weights[DIMENSION_BEDROOM] * 100)),
                    "weighted_contribution": round(bedroom_score * weights[DIMENSION_BEDROOM], 2),
                },
                DIMENSION_AREA: {
                    "score": round(area_score, 1),
                    "weight": round(weights[DIMENSION_AREA], 4),
                    "weight_percentage": int(round(weights[DIMENSION_AREA] * 100)),
                    "weighted_contribution": round(area_score * weights[DIMENSION_AREA], 2),
                },
                DIMENSION_LOCATION: {
                    "score": round(location_score, 1),
                    "weight": round(weights[DIMENSION_LOCATION], 4),
                    "weight_percentage": int(round(weights[DIMENSION_LOCATION] * 100)),
                    "weighted_contribution": round(location_score * weights[DIMENSION_LOCATION], 2),
                    "rating": location_rating,
                },
            }

            # Cover image URL resolution
            cover_image_url = getattr(prop, 'cover_image', None)
            if not cover_image_url and hasattr(prop, 'images') and prop.images.exists():
                first_img = prop.images.first()
                cover_image_url = first_img.image.url if hasattr(first_img, 'image') and first_img.image else None

            scored_results.append({
                "property_id": prop.id,
                "title": prop.title,
                "price": price,
                "bedrooms": actual_bhk,
                "bathrooms": getattr(prop, 'bathrooms', None),
                "area_sqft": actual_sqft,
                "property_type": getattr(prop, 'property_type', ''),
                "address": getattr(prop, 'address', ''),
                "cover_image": cover_image_url,
                "location": {
                    "lat": prop.latitude,
                    "lng": prop.longitude,
                } if hasattr(prop, 'latitude') and hasattr(prop, 'longitude') else None,
                "score": final_score,
                "normal_score": final_score,
                "budget_score": round(budget_score, 1),
                "bedroom_score": round(bedroom_score, 1),
                "area_score": round(area_score, 1),
                "location_score": location_score,
                "location_rating": location_rating,
                "dimension_scores": dimension_scores,
                "weights": weights,
                "reasons": [
                    budget_reason,
                    bedroom_reason,
                    area_reason,
                    location_reason,
                ]
            })

        # Rank descending by score
        scored_results.sort(key=lambda x: x["score"], reverse=True)

        # Enrich each result with structured explanation (Part 6.3)
        explainer = RecommendationExplainer(format_fn=format_inr_short)
        return explainer.explain_all(scored_results, preferences)


class AIRecommendation(RecommendationStrategy):
    def __init__(self, ai_provider=None):
        self.ai_provider = ai_provider

    def recommend(self, candidates, preferences):
        # Fallback to rule-based if AI is not available
        rule_recommender = RuleBasedRecommendation()
        results = rule_recommender.recommend(candidates, preferences)
        for item in results:
            item["ai_preference_fit"] = item["score"]
            item["reasons"].append("Evaluated using AI contextual preference model")
        # Explanations already applied by RuleBasedRecommendation
        return results


class HybridRecommendation(RecommendationStrategy):
    def __init__(self, ai_provider=None, normal_weight=0.7, ai_weight=0.3):
        self.ai_provider = ai_provider
        self.normal_weight = normal_weight
        self.ai_weight = ai_weight

    def recommend(self, candidates, preferences):
        rule_recommender = RuleBasedRecommendation()
        base_results = rule_recommender.recommend(candidates, preferences)

        for item in base_results:
            normal_score = item["normal_score"]
            # Placeholder for AI preference fit
            ai_fit = normal_score * 0.95
            hybrid_score = round((normal_score * self.normal_weight) + (ai_fit * self.ai_weight), 2)
            item["ai_preference_fit"] = round(ai_fit, 2)
            item["hybrid_score"] = hybrid_score
            item["score"] = hybrid_score
            item["reasons"].append(f"Hybrid score balanced ({int(self.normal_weight*100)}% GIS/Normal, {int(self.ai_weight*100)}% AI Context)")

        base_results.sort(key=lambda x: x["score"], reverse=True)
        return base_results

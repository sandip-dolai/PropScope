"""
Configurable deterministic amenity proximity scoring engine.
Evaluates geodetic distances to nearby amenities and assigns normalized
scores (0 - 100) and descriptive proximity labels based on defined thresholds.
"""

# Configurable distance thresholds and corresponding scores per category
DEFAULT_AMENITY_THRESHOLDS = {
    "Metro Station": [
        {"max_km": 1.0, "score": 100.0, "label": "Excellent (<1 km)"},
        {"max_km": 2.5, "score": 75.0, "label": "Good (<2.5 km)"},
        {"max_km": 5.0, "score": 45.0, "label": "Moderate (<5 km)"},
        {"max_km": float('inf'), "score": 20.0, "label": "Poor (>5 km)"}
    ],
    "Hospital": [
        {"max_km": 1.5, "score": 100.0, "label": "Immediate (<1.5 km)"},
        {"max_km": 3.5, "score": 75.0, "label": "Accessible (<3.5 km)"},
        {"max_km": 7.0, "score": 40.0, "label": "Moderate (<7 km)"},
        {"max_km": float('inf'), "score": 15.0, "label": "Far (>7 km)"}
    ],
    "School": [
        {"max_km": 2.0, "score": 100.0, "label": "Walking distance (<2 km)"},
        {"max_km": 4.0, "score": 70.0, "label": "Close (<4 km)"},
        {"max_km": 8.0, "score": 40.0, "label": "Driving distance (<8 km)"},
        {"max_km": float('inf'), "score": 15.0, "label": "Far (>8 km)"}
    ],
    "Shopping Mall": [
        {"max_km": 2.0, "score": 100.0, "label": "Very close (<2 km)"},
        {"max_km": 5.0, "score": 70.0, "label": "Accessible (<5 km)"},
        {"max_km": float('inf'), "score": 30.0, "label": "Distant (>5 km)"}
    ],
    "Park": [
        {"max_km": 1.0, "score": 100.0, "label": "Within reach (<1 km)"},
        {"max_km": 3.0, "score": 70.0, "label": "Nearby (<3 km)"},
        {"max_km": float('inf'), "score": 25.0, "label": "Distant (>3 km)"}
    ],
}


class AmenityProximityScorer:
    """
    Computes normalized category scores based on distance to nearest amenities.
    """

    def __init__(self, thresholds=None):
        self.thresholds = thresholds or DEFAULT_AMENITY_THRESHOLDS

    def score_category(self, category_name: str, distance_km: float) -> tuple[float, str]:
        """
        Returns (score, label) for a given amenity category and distance in km.
        """
        tier_rules = self.thresholds.get(category_name)
        if not tier_rules:
            # Default fallback tier if unknown category
            if distance_km <= 2.0:
                return 100.0, "Close (<2 km)"
            elif distance_km <= 5.0:
                return 60.0, "Moderate (<5 km)"
            return 25.0, "Far (>5 km)"

        for tier in tier_rules:
            if distance_km <= tier["max_km"]:
                return tier["score"], tier["label"]

        return 20.0, "Distant"

    def enrich_nearest_amenities(self, nearest_amenities: list[dict]) -> list[dict]:
        """
        Takes a list of nearest amenity dicts from AmenitySpatialService and enriches
        each with proximity_score and proximity_label.
        """
        enriched = []
        for item in nearest_amenities:
            cat_name = item.get("category_name", "")
            dist_km = item.get("distance_km", 999.0)
            score, label = self.score_category(cat_name, dist_km)

            enriched_item = {
                **item,
                "proximity_score": score,
                "proximity_label": label,
            }
            enriched.append(enriched_item)

        return enriched

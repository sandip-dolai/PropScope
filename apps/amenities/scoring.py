"""
Configurable deterministic amenity proximity and location scoring engine.
Evaluates geodetic distances to nearby amenities and assigns normalized
scores (0 - 100), descriptive proximity labels, and computes composite
location intelligence scores based on weighted pillars:
- Transport (30%)
- Healthcare (20%)
- Education (20%)
- Shopping (15%)
- Recreation (15%)
"""

PILLAR_TRANSPORT = "Transport"
PILLAR_HEALTHCARE = "Healthcare"
PILLAR_EDUCATION = "Education"
PILLAR_SHOPPING = "Shopping"
PILLAR_RECREATION = "Recreation"

ALL_PILLARS = [
    PILLAR_TRANSPORT,
    PILLAR_HEALTHCARE,
    PILLAR_EDUCATION,
    PILLAR_SHOPPING,
    PILLAR_RECREATION,
]

# Standard deterministic weights defined by platform requirements
DEFAULT_LOCATION_WEIGHTS = {
    PILLAR_TRANSPORT: 0.30,
    PILLAR_HEALTHCARE: 0.20,
    PILLAR_EDUCATION: 0.20,
    PILLAR_SHOPPING: 0.15,
    PILLAR_RECREATION: 0.15,
}

# Mapping database amenity category names to canonical pillars
CATEGORY_TO_PILLAR_MAP = {
    "Metro Station": PILLAR_TRANSPORT,
    "Metro": PILLAR_TRANSPORT,
    "Transport": PILLAR_TRANSPORT,
    "Bus Station": PILLAR_TRANSPORT,
    "Train Station": PILLAR_TRANSPORT,
    "Hospital": PILLAR_HEALTHCARE,
    "Healthcare": PILLAR_HEALTHCARE,
    "Clinic": PILLAR_HEALTHCARE,
    "Medical": PILLAR_HEALTHCARE,
    "School": PILLAR_EDUCATION,
    "Education": PILLAR_EDUCATION,
    "College": PILLAR_EDUCATION,
    "University": PILLAR_EDUCATION,
    "Shopping Mall": PILLAR_SHOPPING,
    "Mall": PILLAR_SHOPPING,
    "Shopping": PILLAR_SHOPPING,
    "Supermarket": PILLAR_SHOPPING,
    "Park": PILLAR_RECREATION,
    "Recreation": PILLAR_RECREATION,
    "Garden": PILLAR_RECREATION,
    "Lake": PILLAR_RECREATION,
}

# Configurable distance thresholds and corresponding scores per category
DEFAULT_AMENITY_THRESHOLDS = {
    "Metro Station": [
        {"max_km": 1.0, "score": 100.0, "label": "Excellent (<1 km)"},
        {"max_km": 2.5, "score": 75.0, "label": "Good (<2.5 km)"},
        {"max_km": 5.0, "score": 45.0, "label": "Moderate (<5 km)"},
        {"max_km": float('inf'), "score": 20.0, "label": "Poor (>5 km)"}
    ],
    "Transport": [
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
    "Healthcare": [
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
    "Education": [
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
    "Shopping": [
        {"max_km": 2.0, "score": 100.0, "label": "Very close (<2 km)"},
        {"max_km": 5.0, "score": 70.0, "label": "Accessible (<5 km)"},
        {"max_km": float('inf'), "score": 30.0, "label": "Distant (>5 km)"}
    ],
    "Park": [
        {"max_km": 1.0, "score": 100.0, "label": "Within reach (<1 km)"},
        {"max_km": 3.0, "score": 70.0, "label": "Nearby (<3 km)"},
        {"max_km": float('inf'), "score": 25.0, "label": "Distant (>3 km)"}
    ],
    "Recreation": [
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
            # Check if canonical pillar match exists
            pillar = CATEGORY_TO_PILLAR_MAP.get(category_name)
            if pillar and pillar in self.thresholds:
                tier_rules = self.thresholds[pillar]

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


class DeterministicLocationScoreCalculator:
    """
    Computes deterministic composite location scores across 5 pillars:
    - Transport (30%)
    - Healthcare (20%)
    - Education (20%)
    - Shopping (15%)
    - Recreation (15%)
    """

    def __init__(self, thresholds=None, default_weights=None, pillar_map=None):
        self.scorer = AmenityProximityScorer(thresholds=thresholds)
        self.default_weights = default_weights or DEFAULT_LOCATION_WEIGHTS
        self.pillar_map = pillar_map or CATEGORY_TO_PILLAR_MAP

    @staticmethod
    def get_rating_tier(score: float) -> str:
        """
        Returns a human-readable accessibility classification for a composite score (0-100).
        """
        if score >= 85.0:
            return "Prime Location"
        elif score >= 70.0:
            return "High Accessibility"
        elif score >= 55.0:
            return "Well Connected"
        elif score >= 40.0:
            return "Moderate Accessibility"
        return "Emerging Suburban"

    def normalize_weights(self, custom_weights: dict = None) -> dict:
        """
        Normalizes weights to ensure their sum equals 1.0.
        Accepts pillar names (e.g. 'Transport') or lowercase/case-insensitive variations.
        """
        if not custom_weights:
            return dict(self.default_weights)

        # Map input keys to canonical pillar names
        clean_weights = {}
        for pillar in ALL_PILLARS:
            # Check direct match or case-insensitive match
            val = custom_weights.get(pillar)
            if val is None:
                for k, v in custom_weights.items():
                    if k.strip().lower() == pillar.lower():
                        val = v
                        break
            if val is not None:
                try:
                    clean_weights[pillar] = max(0.0, float(val))
                except (ValueError, TypeError):
                    clean_weights[pillar] = self.default_weights[pillar]
            else:
                clean_weights[pillar] = self.default_weights[pillar]

        total = sum(clean_weights.values())
        if total <= 0:
            return dict(self.default_weights)

        return {k: round(v / total, 4) for k, v in clean_weights.items()}

    def calculate(self, nearest_amenities: list[dict], custom_weights: dict = None) -> dict:
        """
        Computes the composite score and pillar-by-pillar breakdown.
        nearest_amenities can be raw dicts or already enriched dicts.
        """
        weights = self.normalize_weights(custom_weights)

        # If no spatial amenity records exist at all, return standard neutral baseline
        if not nearest_amenities:
            default_score = 80.0
            rating = self.get_rating_tier(default_score)
            breakdown = {
                pillar: {
                    "pillar": pillar,
                    "weight": weights[pillar],
                    "weight_percentage": int(round(weights[pillar] * 100)),
                    "score": default_score,
                    "weighted_contribution": round(default_score * weights[pillar], 2),
                    "amenity_name": "Platform Standard Baseline",
                    "category_name": pillar,
                    "distance_km": None,
                    "distance_m": None,
                    "proximity_label": "Standard Baseline",
                }
                for pillar in ALL_PILLARS
            }
            return {
                "composite_score": default_score,
                "rating": rating,
                "weights": weights,
                "breakdown": breakdown,
            }

        # Group amenities by pillar, keeping the closest / best scoring amenity per pillar
        pillar_candidates = {p: [] for p in ALL_PILLARS}

        for item in nearest_amenities:
            cat_name = item.get("category_name", "")
            pillar = self.pillar_map.get(cat_name) or self.pillar_map.get(cat_name.title())
            if not pillar and cat_name in ALL_PILLARS:
                pillar = cat_name

            if pillar and pillar in pillar_candidates:
                dist_km = item.get("distance_km", 999.0)
                score = item.get("proximity_score")
                label = item.get("proximity_label")
                if score is None or label is None:
                    score, label = self.scorer.score_category(cat_name, dist_km)

                candidate = {
                    "amenity_id": item.get("amenity_id"),
                    "amenity_name": item.get("amenity_name", "Nearby Facility"),
                    "category_name": cat_name,
                    "distance_km": dist_km,
                    "distance_m": item.get("distance_m", round(dist_km * 1000, 1)),
                    "score": float(score),
                    "proximity_label": label,
                }
                pillar_candidates[pillar].append(candidate)

        breakdown = {}
        total_score = 0.0

        for pillar in ALL_PILLARS:
            weight = weights[pillar]
            candidates = pillar_candidates[pillar]

            if candidates:
                # Pick candidate with highest proximity score (or shortest distance if tied)
                best_candidate = max(candidates, key=lambda c: (c["score"], -c["distance_km"]))
                pillar_score = best_candidate["score"]
                amenity_name = best_candidate["amenity_name"]
                category_name = best_candidate["category_name"]
                distance_km = best_candidate["distance_km"]
                distance_m = best_candidate["distance_m"]
                label = best_candidate["proximity_label"]
            else:
                # Default baseline score for missing amenities
                pillar_score = 20.0
                amenity_name = "None within range"
                category_name = pillar
                distance_km = None
                distance_m = None
                label = "No nearby facility (>5 km)"

            weighted_contribution = round(pillar_score * weight, 2)
            total_score += weighted_contribution

            breakdown[pillar] = {
                "pillar": pillar,
                "weight": weight,
                "weight_percentage": int(round(weight * 100)),
                "score": round(pillar_score, 1),
                "weighted_contribution": weighted_contribution,
                "amenity_name": amenity_name,
                "category_name": category_name,
                "distance_km": distance_km,
                "distance_m": distance_m,
                "proximity_label": label,
            }

        composite_score = round(total_score, 1)
        rating = self.get_rating_tier(composite_score)

        return {
            "composite_score": composite_score,
            "rating": rating,
            "weights": weights,
            "breakdown": breakdown,
        }

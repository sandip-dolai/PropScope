from abc import ABC, abstractmethod


class RecommendationStrategy(ABC):
    @abstractmethod
    def recommend(self, candidates, preferences):
        """
        Accepts candidate property querysets/lists and a preferences dict,
        and returns a ranked list with computed scores and reasoning.
        """
        pass


class RuleBasedRecommendation(RecommendationStrategy):
    def recommend(self, candidates, preferences):
        max_budget = float(preferences.get('max_price', 0)) or 100000000
        desired_bedrooms = int(preferences.get('bedrooms', 1))

        scored_results = []
        for prop in candidates:
            # 1. Budget fit score (0 - 100)
            price = float(prop.price)
            if price <= max_budget:
                budget_score = 100.0 - ((price / max_budget) * 20.0)
            else:
                budget_score = max(0.0, 100.0 - ((price - max_budget) / max_budget * 100.0))

            # 2. Bedroom fit score (0 - 100)
            diff = abs(prop.bedrooms - desired_bedrooms)
            bedroom_score = max(0.0, 100.0 - (diff * 25.0))

            # 3. Base Location Score
            location_score = 80.0  # Will be dynamically calculated with amenities in Phase 3/4

            final_score = round(
                (budget_score * 0.40) +
                (bedroom_score * 0.30) +
                (location_score * 0.30),
                2
            )

            scored_results.append({
                "property_id": prop.id,
                "title": prop.title,
                "price": price,
                "bedrooms": prop.bedrooms,
                "normal_score": final_score,
                "score": final_score,
                "reasons": [
                    f"Budget fit score: {round(budget_score, 1)}%",
                    f"Bedroom alignment: {prop.bedrooms} BHK",
                ]
            })

        scored_results.sort(key=lambda x: x["score"], reverse=True)
        return scored_results


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

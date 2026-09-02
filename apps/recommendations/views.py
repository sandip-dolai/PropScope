from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from apps.properties.models import Property, PropertyStatus
from .strategies import RuleBasedRecommendation, AIRecommendation, HybridRecommendation


class RecommendationView(APIView):
    def post(self, request, mode='normal'):
        preferences = request.data.get('preferences', {})
        candidates = Property.objects.filter(status=PropertyStatus.ACTIVE)

        # Apply hard constraints
        max_price = preferences.get('max_price')
        bedrooms = preferences.get('bedrooms')
        if max_price:
            candidates = candidates.filter(price__lte=max_price)
        if bedrooms:
            candidates = candidates.filter(bedrooms__gte=bedrooms)

        if mode == 'ai':
            strategy = AIRecommendation()
        elif mode == 'hybrid':
            strategy = HybridRecommendation()
        else:
            strategy = RuleBasedRecommendation()

        results = strategy.recommend(candidates, preferences)

        return Response({
            "mode": mode,
            "count": len(results),
            "results": results
        })

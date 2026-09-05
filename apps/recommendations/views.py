from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from apps.properties.models import Property, PropertyStatus
from .strategies import (
    RuleBasedRecommendation,
    AIRecommendation,
    HybridRecommendation,
    normalize_dimension_weights,
)


class RecommendationView(APIView):
    """
    Evaluates active properties against hard buyer constraints and ranks them
    using multi-attribute soft preferences (Budget, Bedrooms, Area, Location Quality).
    Supports 'normal', 'ai', and 'hybrid' modes.
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request, mode='normal'):
        preferences = request.data.get('preferences', {})
        candidates = Property.objects.filter(status=PropertyStatus.ACTIVE).select_related('agent')

        applied_constraints = {}

        # 1. Hard Constraint: Price ceiling & floor
        max_price = preferences.get('max_price') or preferences.get('max_budget')
        min_price = preferences.get('min_price') or preferences.get('min_budget')
        if max_price:
            try:
                candidates = candidates.filter(price__lte=float(max_price))
                applied_constraints["max_price"] = float(max_price)
            except (ValueError, TypeError):
                pass
        if min_price:
            try:
                candidates = candidates.filter(price__gte=float(min_price))
                applied_constraints["min_price"] = float(min_price)
            except (ValueError, TypeError):
                pass

        # 2. Hard Constraint: Bedrooms
        bedrooms = preferences.get('bedrooms') or preferences.get('min_bedrooms')
        exact_bedrooms = preferences.get('exact_bedrooms', False)
        if bedrooms:
            try:
                bhk_val = int(bedrooms)
                if exact_bedrooms:
                    candidates = candidates.filter(bedrooms=bhk_val)
                    applied_constraints["bedrooms"] = bhk_val
                    applied_constraints["exact_bedrooms"] = True
                else:
                    candidates = candidates.filter(bedrooms__gte=bhk_val)
                    applied_constraints["bedrooms__gte"] = bhk_val
            except (ValueError, TypeError):
                pass

        # 3. Hard Constraint: Property Type
        prop_type = preferences.get('property_type')
        if prop_type:
            candidates = candidates.filter(property_type=prop_type)
            applied_constraints["property_type"] = prop_type

        # 4. Hard Constraint: Minimum Area
        min_area = preferences.get('min_area_sqft')
        if min_area:
            try:
                candidates = candidates.filter(area_sqft__gte=float(min_area))
                applied_constraints["min_area_sqft"] = float(min_area)
            except (ValueError, TypeError):
                pass

        # 5. Hard Constraint: Spatial Neighborhood Boundary (Area MultiPolygon)
        area_id = preferences.get('area_id') or preferences.get('submarket_id')
        if area_id:
            try:
                from apps.geography.models import Area
                area_obj = Area.objects.filter(id=area_id).first()
                if area_obj and area_obj.boundary:
                    candidates = candidates.filter(location__within=area_obj.boundary)
                    applied_constraints["area_id"] = area_obj.id
                    applied_constraints["area_name"] = area_obj.name
            except Exception:
                pass

        # Select Strategy Mode
        if mode == 'ai':
            strategy = AIRecommendation()
        elif mode == 'hybrid':
            strategy = HybridRecommendation()
        else:
            strategy = RuleBasedRecommendation()

        results = strategy.recommend(candidates, preferences)
        applied_weights = normalize_dimension_weights(preferences.get('weights') or preferences.get('preference_weights'))

        return Response({
            "mode": mode,
            "count": len(results),
            "applied_constraints": applied_constraints,
            "applied_weights": applied_weights,
            "results": results
        })

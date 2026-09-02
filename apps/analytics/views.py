from rest_framework.views import APIView
from rest_framework.response import Response
from django.db.models import Avg, Count, Min, Max
from apps.properties.models import Property, PropertyStatus


class PropertyStatsView(APIView):
    """
    Returns platform-wide or area-specific aggregate real estate statistics.
    """
    def get(self, request):
        stats = Property.objects.filter(status=PropertyStatus.ACTIVE).aggregate(
            total_count=Count('id'),
            avg_price=Avg('price'),
            min_price=Min('price'),
            max_price=Max('price'),
            avg_area=Avg('area_sqft'),
        )
        return Response(stats)

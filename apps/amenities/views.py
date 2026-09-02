from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.contrib.gis.geos import Point
from django.contrib.gis.measure import D
from .models import Amenity, AmenityCategory
from .serializers import AmenitySerializer, AmenityCategorySerializer


class AmenityCategoryListView(generics.ListCreateAPIView):
    queryset = AmenityCategory.objects.all()
    serializer_class = AmenityCategorySerializer


class AmenityListView(generics.ListCreateAPIView):
    queryset = Amenity.objects.all().select_related('category')
    serializer_class = AmenitySerializer


class AmenityNearbyView(APIView):
    """
    Find nearby amenities within radius (km) of a point, optionally filtered by category.
    """
    def get(self, request):
        try:
            lat = float(request.query_params.get('lat'))
            lng = float(request.query_params.get('lng'))
            radius_km = float(request.query_params.get('radius_km', 3.0))
        except (TypeError, ValueError):
            return Response(
                {"error": "lat and lng must be provided as numbers"},
                status=status.HTTP_400_BAD_REQUEST
            )

        category_id = request.query_params.get('category_id')
        point = Point(lng, lat, srid=4326)

        queryset = Amenity.objects.filter(
            location__distance_lte=(point, D(km=radius_km))
        ).select_related('category')

        if category_id:
            queryset = queryset.filter(category_id=category_id)

        serializer = AmenitySerializer(queryset, many=True)
        return Response({
            "center": {"lat": lat, "lng": lng},
            "radius_km": radius_km,
            "count": len(queryset),
            "results": serializer.data
        })

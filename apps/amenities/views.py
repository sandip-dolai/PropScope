from rest_framework import generics, status, permissions
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


class AmenityNearestPointView(APIView):
    """
    Returns the nearest amenity in each category for an arbitrary lat/lng point,
    enriched with proximity scores and detected submarket area.
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        try:
            lat = float(request.query_params.get('lat'))
            lng = float(request.query_params.get('lng'))
        except (TypeError, ValueError):
            return Response(
                {"error": "lat and lng must be provided as valid floating point numbers"},
                status=status.HTTP_400_BAD_REQUEST
            )

        from .services import AmenitySpatialService
        from apps.geography.models import Area

        point = Point(lng, lat, srid=4326)
        nearest = AmenitySpatialService.get_nearest_amenities_for_point(point, enrich_with_scores=True)
        area = Area.objects.filter(boundary__contains=point).first()

        return Response({
            "location": {"lat": lat, "lng": lng},
            "submarket": {
                "id": area.id,
                "name": area.name,
                "city": area.city
            } if area else None,
            "nearest_amenities": nearest
        })


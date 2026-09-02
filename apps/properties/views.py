from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.contrib.gis.geos import Point, GEOSGeometry
from django.contrib.gis.measure import D
from .models import Property, PropertyStatus
from .serializers import PropertySerializer
from .permissions import IsAgentOrAdminOrReadOnly


class PropertyListCreateView(generics.ListCreateAPIView):
    serializer_class = PropertySerializer
    permission_classes = [IsAgentOrAdminOrReadOnly]

    def get_queryset(self):
        queryset = Property.objects.filter(status=PropertyStatus.ACTIVE).select_related('agent')
        
        # Filtering parameters
        min_price = self.request.query_params.get('min_price')
        max_price = self.request.query_params.get('max_price')
        bedrooms = self.request.query_params.get('bedrooms')
        property_type = self.request.query_params.get('property_type')

        if min_price:
            queryset = queryset.filter(price__gte=min_price)
        if max_price:
            queryset = queryset.filter(price__lte=max_price)
        if bedrooms:
            queryset = queryset.filter(bedrooms__gte=bedrooms)
        if property_type:
            queryset = queryset.filter(property_type=property_type)

        return queryset


class PropertyDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Property.objects.all().select_related('agent').prefetch_related('images')
    serializer_class = PropertySerializer
    permission_classes = [IsAgentOrAdminOrReadOnly]


class PropertyRadiusSearchView(APIView):
    """
    Search properties within a specified radius (km) from a latitude/longitude point using PostGIS.
    """
    def get(self, request):
        try:
            lat = float(request.query_params.get('lat'))
            lng = float(request.query_params.get('lng'))
            radius_km = float(request.query_params.get('radius_km', 5.0))
        except (TypeError, ValueError):
            return Response(
                {"error": "lat, lng, and radius_km must be valid floating point numbers"},
                status=status.HTTP_400_BAD_REQUEST
            )

        center_point = Point(lng, lat, srid=4326)
        properties = Property.objects.filter(
            status=PropertyStatus.ACTIVE,
            location__distance_lte=(center_point, D(km=radius_km))
        ).select_related('agent')

        serializer = PropertySerializer(properties, many=True)
        return Response({
            "center": {"lat": lat, "lng": lng},
            "radius_km": radius_km,
            "count": len(properties),
            "results": serializer.data
        })


class PropertyPolygonSearchView(APIView):
    """
    Search properties contained within a GeoJSON Polygon using PostGIS location__within.
    """
    def post(self, request):
        geojson_data = request.data.get('geojson')
        if not geojson_data:
            return Response({"error": "geojson polygon is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            import json
            geometry = GEOSGeometry(json.dumps(geojson_data), srid=4326)
            if geometry.geom_type not in ['Polygon', 'MultiPolygon']:
                return Response({"error": "Geometry must be Polygon or MultiPolygon"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": f"Invalid GeoJSON: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)

        properties = Property.objects.filter(
            status=PropertyStatus.ACTIVE,
            location__within=geometry
        ).select_related('agent')

        serializer = PropertySerializer(properties, many=True)
        return Response({
            "count": len(properties),
            "results": serializer.data
        })

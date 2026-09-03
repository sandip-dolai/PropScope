from rest_framework import generics, status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from django.contrib.gis.geos import Point, GEOSGeometry, Polygon
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
    permission_classes = [permissions.AllowAny]

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
    permission_classes = [permissions.AllowAny]

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


class PropertyBoundingBoxSearchView(APIView):
    """
    Search properties contained within a bounding box (viewport).
    Expects bbox parameter in format: minLng,minLat,maxLng,maxLat
    """
    permission_classes = [permissions.AllowAny]
    def get(self, request):
        bbox_str = request.query_params.get('bbox')
        if not bbox_str:
            return Response({"error": "bbox parameter is required (minLng,minLat,maxLng,maxLat)"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            bbox_coords = [float(c) for c in bbox_str.split(',')]
            if len(bbox_coords) != 4:
                raise ValueError
            
            # min_lng, min_lat, max_lng, max_lat
            bbox_polygon = Polygon.from_bbox(bbox_coords)
            bbox_polygon.srid = 4326
        except ValueError:
            return Response(
                {"error": "bbox must contain 4 comma-separated numbers (minLng,minLat,maxLng,maxLat)"},
                status=status.HTTP_400_BAD_REQUEST
            )

        properties = Property.objects.filter(
            status=PropertyStatus.ACTIVE,
            location__contained=bbox_polygon
        ).select_related('agent')

        serializer = PropertySerializer(properties, many=True)
        return Response({
            "count": len(properties),
            "results": serializer.data
        })


class PropertyNearestAmenitiesView(APIView):
    """
    Returns the nearest amenity in each category (Metro, Hospital, School, Mall, Park)
    for a given property using PostGIS KNN and geodetic distance calculations.
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request, pk):
        try:
            property_obj = Property.objects.get(pk=pk)
        except Property.DoesNotExist:
            return Response(
                {"error": f"Property with id {pk} not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        from apps.amenities.services import AmenitySpatialService
        data = AmenitySpatialService.get_nearest_amenities_for_property(property_obj)
        return Response(data)


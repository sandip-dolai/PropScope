from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from apps.properties.models import Property, PropertyStatus
from apps.properties.serializers import PropertySerializer
from .models import Area
from .serializers import AreaSerializer, AreaDetailSerializer


class AreaListView(generics.ListAPIView):
    queryset = Area.objects.all().order_by('name')
    serializer_class = AreaSerializer
    permission_classes = [permissions.AllowAny]


class AreaDetailView(generics.RetrieveAPIView):
    queryset = Area.objects.all()
    serializer_class = AreaDetailSerializer
    permission_classes = [permissions.AllowAny]


class AreaPropertiesView(APIView):
    """
    Returns all active properties contained within a specific named Area MultiPolygon.
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request, pk):
        try:
            area = Area.objects.get(pk=pk)
        except Area.DoesNotExist:
            return Response({"error": "Area not found"}, status=status.HTTP_404_NOT_FOUND)

        properties = Property.objects.filter(
            status=PropertyStatus.ACTIVE,
            location__within=area.boundary
        ).select_related('agent')

        serializer = PropertySerializer(properties, many=True)
        return Response({
            "area_id": area.id,
            "area_name": area.name,
            "city": area.city,
            "count": len(properties),
            "results": serializer.data
        })

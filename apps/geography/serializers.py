import json
from rest_framework import serializers
from apps.properties.models import Property, PropertyStatus
from apps.properties.serializers import PropertySerializer
from .models import Area


class AreaSerializer(serializers.ModelSerializer):
    boundary_geojson = serializers.SerializerMethodField()
    property_count = serializers.SerializerMethodField()

    class Meta:
        model = Area
        fields = ['id', 'name', 'city', 'description', 'boundary_geojson', 'property_count', 'created_at']

    def get_boundary_geojson(self, obj):
        if obj.boundary:
            return json.loads(obj.boundary.geojson)
        return None

    def get_property_count(self, obj):
        return Property.objects.filter(status=PropertyStatus.ACTIVE, location__within=obj.boundary).count()


class AreaDetailSerializer(AreaSerializer):
    properties = serializers.SerializerMethodField()

    class Meta(AreaSerializer.Meta):
        fields = AreaSerializer.Meta.fields + ['properties']

    def get_properties(self, obj):
        props = Property.objects.filter(status=PropertyStatus.ACTIVE, location__within=obj.boundary).select_related('agent')
        return PropertySerializer(props, many=True).data

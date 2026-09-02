from rest_framework import serializers
from .models import Amenity, AmenityCategory


class AmenityCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = AmenityCategory
        fields = ['id', 'name', 'icon']


class AmenitySerializer(serializers.ModelSerializer):
    category_name = serializers.ReadOnlyField(source='category.name')
    lat = serializers.ReadOnlyField(source='latitude')
    lng = serializers.ReadOnlyField(source='longitude')

    class Meta:
        model = Amenity
        fields = ['id', 'category', 'category_name', 'name', 'address', 'lat', 'lng', 'created_at']

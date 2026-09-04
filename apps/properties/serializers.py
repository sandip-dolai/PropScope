from rest_framework import serializers
from django.contrib.gis.geos import Point
from .models import Property, PropertyImage, PropertyType, PropertyStatus, PropertyInquiry


class PropertyImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = PropertyImage
        fields = ['id', 'image', 'caption', 'is_primary']


class PropertySerializer(serializers.ModelSerializer):
    latitude = serializers.FloatField(write_only=True, required=False)
    longitude = serializers.FloatField(write_only=True, required=False)
    images = PropertyImageSerializer(many=True, read_only=True)
    agent_name = serializers.ReadOnlyField(source='agent.get_full_name')
    price_per_sqft = serializers.ReadOnlyField()
    lat = serializers.ReadOnlyField(source='latitude')
    lng = serializers.ReadOnlyField(source='longitude')

    class Meta:
        model = Property
        fields = [
            'id', 'agent', 'agent_name', 'title', 'description',
            'property_type', 'status', 'price', 'bedrooms', 'bathrooms',
            'area_sqft', 'address', 'latitude', 'longitude', 'lat', 'lng',
            'price_per_sqft', 'images', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'agent', 'agent_name', 'created_at', 'updated_at']

    def create(self, validated_data):
        lat = validated_data.pop('latitude', None)
        lng = validated_data.pop('longitude', None)
        if lat is None or lng is None:
            raise serializers.ValidationError({"location": "Latitude and longitude are required to create a property."})
        validated_data['location'] = Point(lng, lat, srid=4326)
        validated_data['agent'] = self.context['request'].user
        return super().create(validated_data)

    def update(self, instance, validated_data):
        lat = validated_data.pop('latitude', None)
        lng = validated_data.pop('longitude', None)
        if lat is not None and lng is not None:
            instance.location = Point(lng, lat, srid=4326)
        return super().update(instance, validated_data)


class PropertyInquirySerializer(serializers.ModelSerializer):
    property_title = serializers.ReadOnlyField(source='property.title')
    property_price = serializers.ReadOnlyField(source='property.price')
    property_address = serializers.ReadOnlyField(source='property.address')
    property_bedrooms = serializers.ReadOnlyField(source='property.bedrooms')
    agent_name = serializers.ReadOnlyField(source='property.agent.get_full_name')

    class Meta:
        model = PropertyInquiry
        fields = [
            'id', 'property', 'property_title', 'property_price',
            'property_address', 'property_bedrooms', 'agent_name',
            'buyer', 'name', 'email', 'phone', 'message',
            'preferred_visit_date', 'status', 'agent_notes',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'property', 'created_at', 'updated_at']


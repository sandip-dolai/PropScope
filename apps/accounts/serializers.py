from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import UserRole, BuyerProfile, AgentProfile

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    profile = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'role', 'phone_number', 'profile']
        read_only_fields = ['id']

    def get_profile(self, obj):
        if obj.role == UserRole.AGENT and hasattr(obj, 'agent_profile'):
            return {
                'agency_name': obj.agent_profile.agency_name,
                'license_number': obj.agent_profile.license_number,
                'bio': obj.agent_profile.bio
            }
        elif obj.role == UserRole.BUYER and hasattr(obj, 'buyer_profile'):
            return {
                'preferred_city': obj.buyer_profile.preferred_city,
                'preferred_budget': float(obj.buyer_profile.preferred_budget) if obj.buyer_profile.preferred_budget else None
            }
        return None


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'password', 'role', 'phone_number']

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data.get('email', ''),
            password=validated_data['password'],
            role=validated_data.get('role', UserRole.BUYER),
            phone_number=validated_data.get('phone_number', '')
        )
        if user.role == UserRole.BUYER:
            BuyerProfile.objects.create(user=user)
        elif user.role == UserRole.AGENT:
            AgentProfile.objects.create(user=user)
        return user


class AgentShowcaseSerializer(serializers.ModelSerializer):
    agency_name = serializers.SerializerMethodField()
    license_number = serializers.SerializerMethodField()
    bio = serializers.SerializerMethodField()
    is_verified = serializers.SerializerMethodField()
    full_name = serializers.CharField(source='get_full_name', default='')
    monogram = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'username', 'first_name', 'last_name', 'full_name',
            'email', 'phone_number', 'agency_name', 'license_number',
            'bio', 'is_verified', 'monogram'
        ]

    def get_agency_name(self, obj):
        profile = getattr(obj, 'agent_profile', None)
        return profile.agency_name if profile and profile.agency_name else ''

    def get_license_number(self, obj):
        profile = getattr(obj, 'agent_profile', None)
        return profile.license_number if profile and profile.license_number else ''

    def get_bio(self, obj):
        profile = getattr(obj, 'agent_profile', None)
        return profile.bio if profile and profile.bio else ''

    def get_is_verified(self, obj):
        profile = getattr(obj, 'agent_profile', None)
        return bool(profile and profile.is_verified)

    def get_monogram(self, obj):
        first = obj.first_name[:1] if obj.first_name else obj.username[:1]
        last = obj.last_name[:1] if obj.last_name else ''
        return (first + last).upper()


class AdminAgentSerializer(serializers.ModelSerializer):
    agency_name = serializers.SerializerMethodField()
    license_number = serializers.SerializerMethodField()
    bio = serializers.SerializerMethodField()
    is_verified = serializers.SerializerMethodField()
    full_name = serializers.CharField(source='get_full_name', default='')
    listings_count = serializers.SerializerMethodField()
    active_listings_count = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'username', 'first_name', 'last_name', 'full_name',
            'email', 'phone_number', 'agency_name', 'license_number',
            'bio', 'is_verified', 'listings_count', 'active_listings_count',
            'date_joined'
        ]

    def get_agency_name(self, obj):
        profile = getattr(obj, 'agent_profile', None)
        return profile.agency_name if profile and profile.agency_name else ''

    def get_license_number(self, obj):
        profile = getattr(obj, 'agent_profile', None)
        return profile.license_number if profile and profile.license_number else ''

    def get_bio(self, obj):
        profile = getattr(obj, 'agent_profile', None)
        return profile.bio if profile and profile.bio else ''

    def get_is_verified(self, obj):
        profile = getattr(obj, 'agent_profile', None)
        return bool(profile and profile.is_verified)

    def get_listings_count(self, obj):
        return obj.properties.count()

    def get_active_listings_count(self, obj):
        from apps.properties.models import PropertyStatus
        return obj.properties.filter(status=PropertyStatus.ACTIVE).count()




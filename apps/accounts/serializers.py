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

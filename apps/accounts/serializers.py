from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import UserRole, BuyerProfile, AgentProfile

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'role', 'phone_number']
        read_only_fields = ['id']


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

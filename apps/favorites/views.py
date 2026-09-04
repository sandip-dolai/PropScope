from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from apps.properties.models import Property
from apps.properties.serializers import PropertySerializer
from .models import Favorite


class FavoriteListCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        favorites = Favorite.objects.filter(user=request.user).select_related('property')
        properties = [fav.property for fav in favorites]
        serializer = PropertySerializer(properties, many=True)
        return Response(serializer.data)

    def post(self, request):
        property_id = request.data.get('property_id')
        if not property_id:
            return Response({"error": "property_id is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            prop = Property.objects.get(id=property_id)
        except Property.DoesNotExist:
            return Response({"error": "Property not found"}, status=status.HTTP_404_NOT_FOUND)

        favorite, created = Favorite.objects.get_or_create(user=request.user, property=prop)
        return Response({"message": "Favorited successfully", "created": created}, status=status.HTTP_201_CREATED)


class FavoriteDeleteView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, property_id):
        deleted, _ = Favorite.objects.filter(user=request.user, property_id=property_id).delete()
        if deleted:
            return Response({"message": "Favorite removed"}, status=status.HTTP_200_OK)
        return Response({"error": "Favorite not found"}, status=status.HTTP_404_NOT_FOUND)


class FavoriteIdsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        fav_ids = list(Favorite.objects.filter(user=request.user).values_list('property_id', flat=True))
        return Response({"favorite_ids": fav_ids})

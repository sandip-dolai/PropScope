from rest_framework import permissions


class IsAgentOrAdminOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow Agents or Admins to create listings,
    and only the listing's Agent or Admins to edit/delete it.
    """

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user.is_authenticated and (request.user.is_agent or request.user.is_platform_admin)

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        if request.user.is_platform_admin:
            return True
        return obj.agent == request.user

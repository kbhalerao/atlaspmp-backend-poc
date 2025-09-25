from django.contrib.auth import get_user_model
from rest_framework import viewsets, permissions

from .serializers import CustomUserSerializer


class IsAdminOrSelf(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.user and request.user.is_staff:
            return True
        return obj.pk == getattr(request.user, 'pk', None)


class UserViewSet(viewsets.ModelViewSet):
    queryset = get_user_model().objects.all().order_by('id')
    serializer_class = CustomUserSerializer

    def get_permissions(self):
        if self.action in ['list', 'create', 'destroy']:
            permission_classes = [permissions.IsAdminUser]
        elif self.action in ['retrieve', 'partial_update', 'update']:
            permission_classes = [permissions.IsAuthenticated, IsAdminOrSelf]
        else:
            permission_classes = [permissions.IsAuthenticated]
        return [p() for p in permission_classes]

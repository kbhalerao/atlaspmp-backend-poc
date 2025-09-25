from rest_framework import viewsets, permissions
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q

from .models import Project, Task, Tag, Comment
from .serializers import ProjectSerializer, TaskSerializer, TagSerializer, CommentSerializer


class IsOwnerOrReadOnly(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return getattr(obj, 'owner_id', None) == getattr(request.user, 'id', None)


class TagViewSet(viewsets.ModelViewSet):
    queryset = Tag.objects.all().order_by('id')
    serializer_class = TagSerializer
    permission_classes = [IsAuthenticated]


class ProjectViewSet(viewsets.ModelViewSet):
    serializer_class = ProjectSerializer
    permission_classes = [IsAuthenticated, IsOwnerOrReadOnly]

    def get_queryset(self):
        user = self.request.user
        qs = Project.objects.all().order_by('id')
        if not user.is_staff and self.action == 'list':
            qs = qs.filter(owner=user)
        return qs


class TaskViewSet(viewsets.ModelViewSet):
    serializer_class = TaskSerializer
    permission_classes = [IsAuthenticated, IsOwnerOrReadOnly]

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return Task.objects.all().order_by('id')
        # tasks owned by user or assigned to user
        return Task.objects.filter(Q(owner=user) | Q(assignees=user)).distinct().order_by('id')


class CommentViewSet(viewsets.ModelViewSet):
    serializer_class = CommentSerializer
    permission_classes = [IsAuthenticated, IsOwnerOrReadOnly]

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return Comment.objects.all().order_by('id')
        return Comment.objects.filter(owner=user).order_by('id')


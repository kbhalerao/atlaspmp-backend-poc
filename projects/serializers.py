from django.contrib.auth import get_user_model
from rest_framework import serializers

from .models import Project, Task, Tag, Comment


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ['id', 'name', 'color']

class OwnerSerializer(serializers.ModelSerializer):
    class Meta:
        model = get_user_model()
        fields = ['id', 'email', 'first_name', 'last_name']


class ProjectSerializer(serializers.ModelSerializer):
    owner = OwnerSerializer(read_only=True)
    owner_id = serializers.PrimaryKeyRelatedField(
        source='owner',
        queryset=get_user_model().objects.all(),
        write_only=True)
    tags = serializers.PrimaryKeyRelatedField(queryset=Tag.objects.all(), many=True, required=False)

    class Meta:
        model = Project
        fields = ['id', 'title', 'description', 'owner', 'owner_id',
                  'created', 'updated', 'llm_context', 'deadline', 'category', 'tags']
        read_only_fields = ('created', 'updated')


class TaskSerializer(serializers.ModelSerializer):
    owner = OwnerSerializer(read_only=True)
    owner_id = serializers.PrimaryKeyRelatedField(
        source='owner',
        queryset=get_user_model().objects.all(),
        write_only=True
    )
    project = ProjectSerializer(read_only=True)
    project_id = serializers.PrimaryKeyRelatedField(
        source='project',
        queryset=Project.objects.all(),
        write_only=True
    )
    assignees = serializers.PrimaryKeyRelatedField(queryset=get_user_model().objects.all(), many=True, required=False)
    depends_on = serializers.PrimaryKeyRelatedField(queryset=Task.objects.all(), allow_null=True, required=False)
    tags = serializers.PrimaryKeyRelatedField(queryset=Tag.objects.all(), many=True, required=False)

    class Meta:
        model = Task
        fields = [
            'id', 'title', 'description', 'owner', 'owner_id', 'created', 'updated', 'llm_context',
            'project', 'project_id', 'assignees', 'depends_on', 'priority', 'status', 'due_date',
            'estimated_hours', 'tags'
        ]
        read_only_fields = ('created', 'updated')


class CommentSerializer(serializers.ModelSerializer):
    owner = serializers.PrimaryKeyRelatedField(queryset=get_user_model().objects.all())
    task = serializers.PrimaryKeyRelatedField(queryset=Task.objects.all())

    class Meta:
        model = Comment
        fields = ['id', 'title', 'description', 'owner', 'created', 'updated', 'llm_context', 'task']
        read_only_fields = ('created', 'updated')

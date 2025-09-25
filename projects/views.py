from rest_framework import viewsets, permissions
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.response import Response
from django.http import StreamingHttpResponse
from django.db.models import Q
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
import json
import time

from .agent.agent import orm_agent_factory, agent_factory
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

    # allow safe, whitelisted ordering fields
    ALLOWED_ORDERING = {'id', 'title', 'created', 'updated', 'due_date', 'priority', 'status'}

    def get_queryset(self):
        request = self.request
        user = request.user
        qs = Task.objects.all()
        # permission scoping
        if not user.is_staff:
            qs = qs.filter(Q(owner=user) | Q(assignees=user)).distinct()

        # filters
        q = request.query_params.get('q')
        if q:
            qs = qs.filter(Q(title__icontains=q) | Q(description__icontains=q) | Q(tags__name__icontains=q) | Q(
                project__title__icontains=q))

        status_f = request.query_params.get('status')
        if status_f:
            qs = qs.filter(status=status_f)

        priority_f = request.query_params.get('priority')
        if priority_f:
            qs = qs.filter(priority=priority_f)

        project = request.query_params.get('project')
        if project:
            qs = qs.filter(project_id=project)

        tag = request.query_params.get('tag')
        if tag:
            try:
                tag_id = int(tag)
                qs = qs.filter(tags__id=tag_id)
            except ValueError:
                qs = qs.filter(tags__name=tag)

        assigned = request.query_params.get('assigned')
        if assigned:
            try:
                assigned_id = int(assigned)
                qs = qs.filter(assignees__id=assigned_id)
            except ValueError:
                qs = qs.none()

        mine = request.query_params.get('mine')
        if mine and mine.lower() in {'1', 'true', 'yes'}:
            qs = qs.filter(owner=user)

        include_assigned = request.query_params.get('include_assigned')
        if include_assigned and include_assigned.lower() in {'0', 'false', 'no'}:
            # if false, restrict to owner-only view regardless of staff flag (still harmless for staff)
            qs = qs.filter(owner=user)

        # ordering
        ordering = request.query_params.get('ordering') or 'id'
        if ordering:
            raw = ordering
            desc = raw.startswith('-')
            field = raw[1:] if desc else raw
            if field in self.ALLOWED_ORDERING:
                qs = qs.order_by(raw)
            else:
                qs = qs.order_by('id')

        return qs


class CommentViewSet(viewsets.ModelViewSet):
    serializer_class = CommentSerializer
    permission_classes = [IsAuthenticated, IsOwnerOrReadOnly]

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return Comment.objects.all().order_by('id')
        return Comment.objects.filter(owner=user).order_by('id')


class AgentChatView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        # Parse body
        body = request.data or {}
        message = body.get('message', '')
        previous_messages = body.get('previous_messages', [])
        context = body.get('context', {}) or {}
        options = body.get('options', {}) or {}

        # Build a concise context snapshot (without hitting the LLM yet)
        ctx_type = context.get('type', 'none')
        ctx_id = context.get('id')
        if ctx_type == 'task' and ctx_id:
            try:
                t = Task.objects.get(id=ctx_id)
                # minimal snapshot for tests
                ctx_summary = TaskSerializer(t).data
            except Task.DoesNotExist:
                ctx_summary = {'type': 'task', 'id': ctx_id, 'missing': True}
        elif ctx_type == 'project' and ctx_id:
            try:
                p = Project.objects.get(id=ctx_id)
                ctx_summary = ProjectSerializer(p).data
            except Project.DoesNotExist:
                ctx_summary = {'type': 'project', 'id': ctx_id, 'missing': True}
        else:
            ctx_summary = {'type': 'none'}

        ctx_summary['request'] = message

        # Test-friendly meta: allow toggling change via options
        simulate_change = bool(options.get('simulate_change'))
        last_action = options.get('last_action') if simulate_change else None

        if simulate_change:
            response = {
                'messages': [
                    {'role': 'user', 'content': message},
                    {'role': 'assistant', 'content': 'Acknowledged'}
                ],
                'tool_calls': [],
                'result': {'echo': True, 'context': ctx_summary},
                'meta': {
                    'changed': simulate_change,
                    'last_action': last_action,
                    'user_id': getattr(request.user, 'id', None),
                }
            }
            return Response(response)

        prompt = (f"Respond to the request using optional context and previous messages. "
                  f"\n\n{ctx_summary}")

        agent = agent_factory(user=request.user)
        response = agent.run_sync(prompt, message_history=previous_messages)
        return Response(response.output)


class AgentChatStreamView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Build an SSE stream that sends a few events and closes
        def event_stream():
            # event: hello
            yield f"event: hello\n"
            yield f"data: {json.dumps({'user_id': getattr(request.user, 'id', None)})}\n\n"
            time.sleep(0.01)
            # event: progress
            yield f"event: progress\n"
            yield f"data: {json.dumps({'stage': 'processing'})}\n\n"
            time.sleep(0.01)
            # event: done
            yield f"event: done\n"
            yield f"data: {json.dumps({'ok': True})}\n\n"

        return StreamingHttpResponse(event_stream(), content_type='text/event-stream')


@login_required
def spv_view(request):
    return render(request, 'spv.html')

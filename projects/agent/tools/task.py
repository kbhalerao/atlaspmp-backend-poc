from typing import List, Optional, Dict, Any
from django.db import transaction
from django.utils import timezone
from pydantic import BaseModel, Field

from ...models import Task, Project
from .utils import can_write


class TaskOut(BaseModel):
    id: int
    title: str
    description: str
    owner_id: int
    project_id: int
    assignee_ids: List[int] = []
    depends_on_id: Optional[int] = None
    priority: str
    status: str
    due_date: Optional[str] = None
    estimated_hours: Optional[float] = None
    tag_ids: List[int] = []
    llm_context: Dict[str, Any] = {}


class CreateTaskIn(BaseModel):
    title: str
    description: str
    project_id: int
    assignee_ids: List[int] = Field(default_factory=list)
    depends_on_id: Optional[int] = None
    priority: str = "MEDIUM"
    status: str = "TODO"
    due_date: Optional[str] = None
    estimated_hours: Optional[float] = None
    tag_ids: List[int] = Field(default_factory=list)
    llm_notes: Optional[str] = Field(default=None, description="Optional free-text notes for llm_context summary.")


class UpdateTaskIn(BaseModel):
    task_id: int
    title: Optional[str] = None
    description: Optional[str] = None
    assignee_ids: Optional[List[int]] = None
    depends_on_id: Optional[int] = Field(default=None)
    priority: Optional[str] = None
    status: Optional[str] = None
    due_date: Optional[str] = None
    estimated_hours: Optional[float] = None
    tag_ids: Optional[List[int]] = None
    llm_notes: Optional[str] = None


class GetTaskIn(BaseModel):
    task_id: int


class ListTasksIn(BaseModel):
    project_id: Optional[int] = None
    owned_only: bool = False
    include_assigned: bool = True


class DeleteTaskIn(BaseModel):
    task_id: int


def serialize_task(task: Task) -> TaskOut:
    return TaskOut(
        id=task.id,
        title=task.title,
        description=task.description,
        owner_id=task.owner_id,
        project_id=task.project_id,
        assignee_ids=list(task.assignees.values_list('id', flat=True)),
        depends_on_id=task.depends_on_id,
        priority=task.priority,
        status=task.status,
        due_date=task.due_date.isoformat() if task.due_date else None,
        estimated_hours=float(task.estimated_hours) if task.estimated_hours is not None else None,
        tag_ids=list(task.tags.values_list('id', flat=True)),
        llm_context=task.llm_context or {},
    )


@transaction.atomic
def tool_create_task(user, payload: CreateTaskIn) -> TaskOut:
    project = Project.objects.get(id=payload.project_id)
    if not can_write(user, project.owner_id):
        raise PermissionError("Not allowed to create tasks in this project")

    llm_context = {
        **(project.llm_context or {}),
        "source": "agent",
        "last_action": "create",
        "actor_user_id": getattr(user, 'id', None),
        "actor_email": getattr(user, 'email', None),
        "summary_text": payload.llm_notes or f"Task '{payload.title}' created via agent",
        "timestamp": timezone.now().isoformat(),
    }

    task = Task.objects.create(
        title=payload.title,
        description=payload.description,
        owner=project.owner,
        project=project,
        priority=payload.priority,
        status=payload.status,
        llm_context=llm_context,
    )

    if payload.depends_on_id:
        task.depends_on_id = payload.depends_on_id
    if payload.due_date:
        from django.utils.dateparse import parse_datetime
        task.due_date = parse_datetime(payload.due_date)
    if payload.estimated_hours is not None:
        task.estimated_hours = payload.estimated_hours
    task.save()

    if payload.assignee_ids:
        task.assignees.set(payload.assignee_ids)
    if payload.tag_ids:
        task.tags.set(payload.tag_ids)

    return serialize_task(task)


def tool_get_task(user, payload: GetTaskIn) -> TaskOut:
    task = Task.objects.get(id=payload.task_id)
    if not getattr(user, 'is_staff', False):
        if task.owner_id != getattr(user, 'id', None) and not task.assignees.filter(id=user.id).exists():
            raise PermissionError("Not allowed to view this task")
    return serialize_task(task)


def tool_list_tasks(user, payload: ListTasksIn) -> List[TaskOut]:
    from django.db.models import Q
    qs = Task.objects.all()
    if not getattr(user, 'is_staff', False):
        filt = Q(owner=user)
        if payload.include_assigned:
            filt |= Q(assignees=user)
        qs = qs.filter(filt).distinct()
    if payload.project_id:
        qs = qs.filter(project_id=payload.project_id)
    if payload.owned_only:
        qs = qs.filter(owner=user)
    qs = qs.order_by('id')
    return [serialize_task(t) for t in qs]


@transaction.atomic
def tool_update_task(user, payload: UpdateTaskIn) -> TaskOut:
    task = Task.objects.select_for_update().get(id=payload.task_id)
    if not can_write(user, task.owner_id):
        raise PermissionError("Not allowed to update this task")

    if payload.title is not None:
        task.title = payload.title
    if payload.description is not None:
        task.description = payload.description
    if payload.priority is not None:
        task.priority = payload.priority
    if payload.status is not None:
        task.status = payload.status
    if payload.depends_on_id is not None:
        task.depends_on_id = payload.depends_on_id
    if payload.due_date is not None:
        from django.utils.dateparse import parse_datetime
        task.due_date = parse_datetime(payload.due_date) if payload.due_date else None
    if payload.estimated_hours is not None:
        task.estimated_hours = payload.estimated_hours

    if payload.assignee_ids is not None:
        task.assignees.set(payload.assignee_ids)
    if payload.tag_ids is not None:
        task.tags.set(payload.tag_ids)

    lc = task.llm_context or {}
    lc.update({
        "source": "agent",
        "last_action": "update",
        "actor_user_id": getattr(user, 'id', None),
        "actor_email": getattr(user, 'email', None),
        "summary_text": payload.llm_notes or lc.get("summary_text"),
        "timestamp": timezone.now().isoformat(),
    })
    task.llm_context = lc

    task.save()
    return serialize_task(task)


@transaction.atomic
def tool_delete_task(user, payload: DeleteTaskIn) -> Dict[str, Any]:
    task = Task.objects.get(id=payload.task_id)
    if not can_write(user, task.owner_id):
        raise PermissionError("Not allowed to delete this task")
    task.delete()
    return {"deleted": True, "task_id": payload.task_id}

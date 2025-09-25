from typing import List, Optional, Dict, Any
from django.db import transaction
from django.utils import timezone
from pydantic import BaseModel, Field

from ...models import Project
from .utils import can_write


class ProjectOut(BaseModel):
    id: int
    title: str
    description: str
    owner_id: int
    created: str
    updated: str
    llm_context: Dict[str, Any] = {}
    deadline: Optional[str] = None
    category: str = ""
    tag_ids: List[int] = []


class CreateProjectIn(BaseModel):
    title: str
    description: str
    owner_id: int
    deadline: Optional[str] = None
    category: Optional[str] = ""
    tag_ids: List[int] = Field(default_factory=list)
    llm_notes: Optional[str] = None


class UpdateProjectIn(BaseModel):
    project_id: int
    title: Optional[str] = None
    description: Optional[str] = None
    deadline: Optional[str] = None
    category: Optional[str] = None
    tag_ids: Optional[List[int]] = None
    llm_notes: Optional[str] = None


class GetProjectIn(BaseModel):
    project_id: int


class ListProjectsIn(BaseModel):
    owned_only: bool = True
    category: Optional[str] = None


class DeleteProjectIn(BaseModel):
    project_id: int


def serialize_project(p: Project) -> ProjectOut:
    return ProjectOut(
        id=p.id,
        title=p.title,
        description=p.description,
        owner_id=p.owner_id,
        created=p.created.isoformat(),
        updated=p.updated.isoformat(),
        llm_context=p.llm_context or {},
        deadline=p.deadline.isoformat() if p.deadline else None,
        category=p.category or "",
        tag_ids=list(p.tags.values_list('id', flat=True)),
    )


@transaction.atomic
def tool_create_project(user, payload: CreateProjectIn) -> ProjectOut:
    owner_id = payload.owner_id
    if not getattr(user, 'is_staff', False) and owner_id != getattr(user, 'id', None):
        raise PermissionError("Not allowed to create project for another user")

    from django.utils.dateparse import parse_datetime
    llm_context = {
        "source": "agent",
        "last_action": "create",
        "actor_user_id": getattr(user, 'id', None),
        "actor_email": getattr(user, 'email', None),
        "summary_text": payload.llm_notes or f"Project '{payload.title}' created via agent",
        "timestamp": timezone.now().isoformat(),
    }
    p = Project.objects.create(
        title=payload.title,
        description=payload.description,
        owner_id=owner_id,
        deadline=parse_datetime(payload.deadline) if payload.deadline else None,
        category=payload.category or "",
        llm_context=llm_context,
    )
    if payload.tag_ids:
        p.tags.set(payload.tag_ids)
    return serialize_project(p)


def tool_get_project(user, payload: GetProjectIn) -> ProjectOut:
    p = Project.objects.get(id=payload.project_id)
    if not getattr(user, 'is_staff', False) and p.owner_id != getattr(user, 'id', None):
        raise PermissionError("Not allowed to view this project")
    return serialize_project(p)


def tool_list_projects(user, payload: ListProjectsIn) -> List[ProjectOut]:
    qs = Project.objects.all().order_by('id')
    if not getattr(user, 'is_staff', False):
        qs = qs.filter(owner=user)
    if payload.category:
        qs = qs.filter(category=payload.category)
    return [serialize_project(p) for p in qs]


@transaction.atomic
def tool_update_project(user, payload: UpdateProjectIn) -> ProjectOut:
    p = Project.objects.select_for_update().get(id=payload.project_id)
    if not can_write(user, p.owner_id):
        raise PermissionError("Not allowed to update this project")

    from django.utils.dateparse import parse_datetime
    if payload.title is not None:
        p.title = payload.title
    if payload.description is not None:
        p.description = payload.description
    if payload.deadline is not None:
        p.deadline = parse_datetime(payload.deadline) if payload.deadline else None
    if payload.category is not None:
        p.category = payload.category or ""
    if payload.tag_ids is not None:
        p.tags.set(payload.tag_ids)

    lc = p.llm_context or {}
    lc.update({
        "source": "agent",
        "last_action": "update",
        "actor_user_id": getattr(user, 'id', None),
        "actor_email": getattr(user, 'email', None),
        "summary_text": payload.llm_notes or lc.get("summary_text"),
        "timestamp": timezone.now().isoformat(),
    })
    p.llm_context = lc
    p.save()
    return serialize_project(p)


@transaction.atomic
def tool_delete_project(user, payload: DeleteProjectIn) -> Dict[str, Any]:
    p = Project.objects.get(id=payload.project_id)
    if not can_write(user, p.owner_id):
        raise PermissionError("Not allowed to delete this project")
    p.delete()
    return {"deleted": True, "project_id": payload.project_id}

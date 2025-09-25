from typing import List, Optional, Dict, Any
from django.db import transaction
from django.utils import timezone
from pydantic import BaseModel

from ...models import Comment, Task
from .utils import can_write


class CommentOut(BaseModel):
    id: int
    title: str
    description: str
    owner_id: int
    task_id: int
    created: str
    updated: str
    llm_context: Dict[str, Any] = {}


class CreateCommentIn(BaseModel):
    title: str
    description: str
    task_id: int
    llm_notes: Optional[str] = None


class UpdateCommentIn(BaseModel):
    comment_id: int
    title: Optional[str] = None
    description: Optional[str] = None
    llm_notes: Optional[str] = None


class GetCommentIn(BaseModel):
    comment_id: int


class ListCommentsIn(BaseModel):
    task_id: Optional[int] = None
    owned_only: bool = True


class DeleteCommentIn(BaseModel):
    comment_id: int


def serialize_comment(c: Comment) -> CommentOut:
    return CommentOut(
        id=c.id,
        title=c.title,
        description=c.description,
        owner_id=c.owner_id,
        task_id=c.task_id,
        created=c.created.isoformat(),
        updated=c.updated.isoformat(),
        llm_context=c.llm_context or {},
    )


@transaction.atomic
def tool_create_comment(user, payload: CreateCommentIn) -> CommentOut:
    task = Task.objects.get(id=payload.task_id)
    if not getattr(user, 'is_staff', False):
        if task.owner_id != getattr(user, 'id', None) and not task.assignees.filter(id=user.id).exists():
            raise PermissionError("Not allowed to comment on this task")

    llm_context = {
        "source": "agent",
        "last_action": "create",
        "actor_user_id": getattr(user, 'id', None),
        "actor_email": getattr(user, 'email', None),
        "summary_text": payload.llm_notes or f"Comment created on task {task.id}",
        "timestamp": timezone.now().isoformat(),
    }
    c = Comment.objects.create(
        title=payload.title,
        description=payload.description,
        owner=user,
        task=task,
        llm_context=llm_context,
    )
    return serialize_comment(c)


def tool_get_comment(user, payload: GetCommentIn) -> CommentOut:
    c = Comment.objects.get(id=payload.comment_id)
    if not getattr(user, 'is_staff', False) and c.owner_id != getattr(user, 'id', None):
        raise PermissionError("Not allowed to view this comment")
    return serialize_comment(c)


def tool_list_comments(user, payload: ListCommentsIn) -> List[CommentOut]:
    qs = Comment.objects.all().order_by('id')
    if not getattr(user, 'is_staff', False):
        qs = qs.filter(owner=user)
    if payload.task_id:
        qs = qs.filter(task_id=payload.task_id)
    return [serialize_comment(c) for c in qs]


@transaction.atomic
def tool_update_comment(user, payload: UpdateCommentIn) -> CommentOut:
    c = Comment.objects.select_for_update().get(id=payload.comment_id)
    if not can_write(user, c.owner_id):
        raise PermissionError("Not allowed to update this comment")
    if payload.title is not None:
        c.title = payload.title
    if payload.description is not None:
        c.description = payload.description
    lc = c.llm_context or {}
    lc.update({
        "source": "agent",
        "last_action": "update",
        "actor_user_id": getattr(user, 'id', None),
        "actor_email": getattr(user, 'email', None),
        "summary_text": payload.llm_notes or lc.get("summary_text"),
        "timestamp": timezone.now().isoformat(),
    })
    c.llm_context = lc
    c.save()
    return serialize_comment(c)


@transaction.atomic
def tool_delete_comment(user, payload: DeleteCommentIn) -> Dict[str, Any]:
    c = Comment.objects.get(id=payload.comment_id)
    if not can_write(user, c.owner_id):
        raise PermissionError("Not allowed to delete this comment")
    c.delete()
    return {"deleted": True, "comment_id": payload.comment_id}

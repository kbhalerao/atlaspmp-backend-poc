from typing import Any
from django.db.models import Q

from ...models import Task


def can_write(user: Any, obj_owner_id: int) -> bool:
    return bool(getattr(user, 'is_staff', False) or getattr(user, 'id', None) == obj_owner_id)


def visible_tasks_qs(user: Any):
    if getattr(user, 'is_staff', False):
        return Task.objects.all()
    return Task.objects.filter(Q(owner=user) | Q(assignees=user)).distinct()

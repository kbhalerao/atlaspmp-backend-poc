from typing import List, Optional, Dict, Any
from pydantic import BaseModel

from ...models import Tag


class TagOut(BaseModel):
    id: int
    name: str
    color: str


class CreateTagIn(BaseModel):
    name: str
    color: str = "#000000"


class UpdateTagIn(BaseModel):
    tag_id: int
    name: Optional[str] = None
    color: Optional[str] = None


class GetTagIn(BaseModel):
    tag_id: int


class ListTagsIn(BaseModel):
    name_contains: Optional[str] = None


class DeleteTagIn(BaseModel):
    tag_id: int


def serialize_tag(tag: Tag) -> TagOut:
    return TagOut(id=tag.id, name=tag.name, color=tag.color)


def tool_create_tag(user, payload: CreateTagIn) -> TagOut:
    tag = Tag.objects.create(name=payload.name, color=payload.color)
    return serialize_tag(tag)


def tool_get_tag(user, payload: GetTagIn) -> TagOut:
    tag = Tag.objects.get(id=payload.tag_id)
    return serialize_tag(tag)


def tool_list_tags(user, payload: ListTagsIn) -> List[TagOut]:
    qs = Tag.objects.all().order_by('id')
    if payload.name_contains:
        qs = qs.filter(name__icontains=payload.name_contains)
    return [serialize_tag(t) for t in qs]


def tool_update_tag(user, payload: UpdateTagIn) -> TagOut:
    tag = Tag.objects.get(id=payload.tag_id)
    if payload.name is not None:
        tag.name = payload.name
    if payload.color is not None:
        tag.color = payload.color
    tag.save()
    return serialize_tag(tag)


def tool_delete_tag(user, payload: DeleteTagIn) -> Dict[str, Any]:
    Tag.objects.filter(id=payload.tag_id).delete()
    return {"deleted": True, "tag_id": payload.tag_id}

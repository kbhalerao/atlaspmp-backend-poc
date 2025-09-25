from typing import Dict, List, Any, Optional, Type, Union
from pydantic import BaseModel, create_model, Field
from django.db import models, transaction
from django.db.models import Q
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.apps import apps

from ...models import Project, Task, Tag, Comment
from .utils import can_write

User = get_user_model()

# Map of models that can be accessed through the ORM tool
ALLOWED_MODELS = {
    'project': Project,
    'task': Task, 
    'tag': Tag,
    'comment': Comment,
}

class ModelAction(BaseModel):
    """Base class for all model actions"""
    model_name: str
    
class CreateAction(ModelAction):
    """Generic create action for any model"""
    data: Dict[str, Any]

class ReadAction(ModelAction):
    """Generic read action for a single instance"""
    id: int
    
class UpdateAction(ModelAction):
    """Generic update action for any model"""
    id: int
    data: Dict[str, Any]
    
class DeleteAction(ModelAction):
    """Generic delete action for any model"""
    id: int
    
class QueryAction(ModelAction):
    """Generic query action with filters"""
    filters: Optional[Dict[str, Any]] = None
    limit: Optional[int] = 100

def get_model_fields(model_class: Type[models.Model]) -> Dict[str, Any]:
    """
    Inspect model fields and return a dictionary of field names and their types.
    """
    field_info = {}
    for field in model_class._meta.get_fields():
        if field.is_relation:
            if field.many_to_many:
                field_info[f"{field.name}_ids"] = (List[int], [])
            elif field.many_to_one:
                field_info[f"{field.name}_id"] = (Optional[int], None)
            # Handle other relationship types as needed
        else:
            # Map Django field types to Python types
            if isinstance(field, models.CharField) or isinstance(field, models.TextField):
                field_info[field.name] = (str, ...)
            elif isinstance(field, models.IntegerField):
                field_info[field.name] = (int, ...)
            elif isinstance(field, models.BooleanField):
                field_info[field.name] = (bool, ...)
            elif isinstance(field, models.DateTimeField) or isinstance(field, models.DateField):
                field_info[field.name] = (Optional[str], None)
            elif isinstance(field, models.DecimalField) or isinstance(field, models.FloatField):
                field_info[field.name] = (Optional[float], None)
            # Add more field type mappings as needed
    
    # Remove fields that shouldn't be directly set
    for field_name in ['id', 'created', 'updated']:
        if field_name in field_info:
            del field_info[field_name]
            
    return field_info

def serialize_instance(instance: models.Model) -> Dict[str, Any]:
    """
    Convert a model instance to a dictionary representation.
    Handle relationships appropriately.
    """
    data = {}
    for field in instance._meta.get_fields():
        if field.is_relation:
            if field.many_to_many:
                data[f"{field.name}_ids"] = list(getattr(instance, field.name).values_list('id', flat=True))
            elif field.many_to_one:
                related_id = getattr(instance, f"{field.name}_id", None)
                if related_id:
                    data[f"{field.name}_id"] = related_id
        else:
            value = getattr(instance, field.name, None)
            if field.name == 'llm_context' and not value:
                value = {}
            if value is not None:
                # Handle special types like datetime and Decimal
                if hasattr(value, 'isoformat'):  # For DateTime fields
                    value = value.isoformat()
                elif hasattr(value, '__float__'):  # For Decimal fields
                    value = float(value)
                data[field.name] = value
    
    return data

@transaction.atomic
def tool_orm_action(user: User, action: Union[CreateAction, ReadAction, UpdateAction, DeleteAction, QueryAction]) -> Dict[str, Any]:
    """
    Unified ORM tool that handles all CRUD operations for any allowed model
    based on the action type and parameters.
    """
    model_name = action.model_name.lower()
    if model_name not in ALLOWED_MODELS:
        raise ValueError(f"Model '{model_name}' not allowed or doesn't exist")
    
    model_class = ALLOWED_MODELS[model_name]
    
    # Handle CREATE
    if isinstance(action, CreateAction):
        data = action.data.copy()
        
        # Handle special cases and permissions
        if model_name == 'task':
            project_id = data.get('project_id')
            if project_id:
                project = Project.objects.get(id=project_id)
                if not can_write(user, project.owner_id):
                    raise PermissionError(f"Not allowed to create {model_name}")
                data['owner_id'] = project.owner_id
        else:
            # Default ownership
            if 'owner_id' not in data and hasattr(model_class, 'owner'):
                data['owner_id'] = user.id
                
        # Extract M2M fields to set after creation
        m2m_fields = {}
        for field in model_class._meta.get_fields():
            if field.many_to_many:
                field_ids = data.pop(f"{field.name}_ids", None)
                if field_ids is not None:
                    m2m_fields[field.name] = field_ids
                    
        # Handle llm_context
        llm_context = {
            "source": "agent",
            "last_action": "create",
            "actor_user_id": getattr(user, 'id', None),
            "actor_email": getattr(user, 'email', None),
            "summary_text": data.pop('llm_notes', f"{model_name.title()} created via agent"),
            "timestamp": timezone.now().isoformat(),
        }
        data['llm_context'] = llm_context
        
        # Create instance
        instance = model_class.objects.create(**data)
        
        # Set M2M fields
        for field_name, ids in m2m_fields.items():
            if ids:
                getattr(instance, field_name).set(ids)
                
        return serialize_instance(instance)
    
    # Handle READ
    elif isinstance(action, ReadAction):
        instance = model_class.objects.get(id=action.id)
        
        # Permission check
        if not getattr(user, 'is_staff', False):
            if hasattr(instance, 'owner'):
                owner_id = getattr(instance, 'owner_id')
                if owner_id != user.id:
                    # For tasks, also check if user is an assignee
                    if model_name == 'task' and not instance.assignees.filter(id=user.id).exists():
                        raise PermissionError(f"Not allowed to view this {model_name}")
                    elif model_name != 'task':
                        raise PermissionError(f"Not allowed to view this {model_name}")
        
        return serialize_instance(instance)
    
    # Handle UPDATE
    elif isinstance(action, UpdateAction):
        instance = model_class.objects.select_for_update().get(id=action.id)
        
        # Permission check
        if not can_write(user, getattr(instance, 'owner_id', None)):
            raise PermissionError(f"Not allowed to update this {model_name}")
            
        data = action.data.copy()
        
        # Extract M2M fields to set after update
        m2m_fields = {}
        for field in model_class._meta.get_fields():
            if field.many_to_many:
                field_ids = data.pop(f"{field.name}_ids", None)
                if field_ids is not None:
                    m2m_fields[field.name] = field_ids
        
        # Update llm_context
        lc = getattr(instance, 'llm_context', {}) or {}
        lc.update({
            "source": "agent",
            "last_action": "update",
            "actor_user_id": getattr(user, 'id', None),
            "actor_email": getattr(user, 'email', None),
            "summary_text": data.pop('llm_notes', lc.get("summary_text")),
            "timestamp": timezone.now().isoformat(),
        })
        data['llm_context'] = lc
        
        # Update fields
        for field, value in data.items():
            setattr(instance, field, value)
        
        instance.save()
        
        # Update M2M fields
        for field_name, ids in m2m_fields.items():
            getattr(instance, field_name).set(ids)
            
        return serialize_instance(instance)
    
    # Handle DELETE
    elif isinstance(action, DeleteAction):
        instance = model_class.objects.get(id=action.id)
        
        # Permission check
        if not can_write(user, getattr(instance, 'owner_id', None)):
            raise PermissionError(f"Not allowed to delete this {model_name}")
            
        instance_id = instance.id
        instance.delete()
        
        return {"deleted": True, f"{model_name}_id": instance_id}
    
    # Handle QUERY
    elif isinstance(action, QueryAction):
        queryset = model_class.objects.all()
        
        # Apply filters
        if action.filters:
            queryset = queryset.filter(**action.filters)
            
        # Apply permission filters
        if not getattr(user, 'is_staff', False) and hasattr(model_class, 'owner'):
            queryset = queryset.filter(
                Q(owner=user) | 
                (Q(assignees=user) if hasattr(model_class, 'assignees') else Q())
            ).distinct()
            
        # Apply limit
        if action.limit:
            queryset = queryset[:action.limit]
            
        return [serialize_instance(instance) for instance in queryset]
    
    return {"error": "Invalid action type"}
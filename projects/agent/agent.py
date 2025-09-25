from typing import Any, Dict, Union
from pydantic_ai import Agent, RunContext
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.grok import GrokProvider
from django.conf import settings
from .tools.generic import CreateAction, ReadAction, QueryAction, UpdateAction, DeleteAction, tool_orm_action
import logfire

model = OpenAIChatModel('grok-code-fast-1',
                        provider=GrokProvider(api_key=settings.XAI_API_KEY),
                        )

from .tools.task import (
    tool_create_task, tool_get_task, tool_list_tasks, tool_update_task, tool_delete_task,
    CreateTaskIn, UpdateTaskIn, GetTaskIn, ListTasksIn, DeleteTaskIn, TaskOut,
)
from .tools.project import (
    tool_create_project, tool_get_project, tool_list_projects, tool_update_project, tool_delete_project,
    CreateProjectIn, UpdateProjectIn, GetProjectIn, ListProjectsIn, DeleteProjectIn, ProjectOut,
)
from .tools.tag import (
    tool_create_tag, tool_get_tag, tool_list_tags, tool_update_tag, tool_delete_tag,
    CreateTagIn, UpdateTagIn, GetTagIn, ListTagsIn, DeleteTagIn, TagOut,
)
from .tools.comment import (
    tool_create_comment, tool_get_comment, tool_list_comments, tool_update_comment, tool_delete_comment,
    CreateCommentIn, UpdateCommentIn, GetCommentIn, ListCommentsIn, DeleteCommentIn, CommentOut,
)


SYSTEM_PROMPT = """
You are a project manager with the ability to call the database using several tools.
Follow permissions equivalent to the REST API:
- Only the task owner or staff can update/delete a task.
- Non-staff can see tasks they own or are assigned to.

Maintain and enrich the llm_context field to store brief, helpful context for future RAG use and for traceability.
Keep it concise and structured, without replicating information from the rest of the fields
 (e.g., source, last_action, actor_user_id, summary_text).
"""


def agent_factory(user=None):
    """Create an Agent pre-wired with task CRUD tools.

    Pass the current user (request.user) when constructing the agent so tools can
    enforce permissions and attribute actions.
    """
    agent = Agent(
        model=model,
        name="Project DB handler agent",
        system_prompt=SYSTEM_PROMPT,
        output_type=dict,
    )

    # Register tools. Each tool wraps underlying function adding the user context.
    # We annotate input and output types for pydantic_ai.

    # Task tools
    @agent.tool
    def create_task(ctx: RunContext[str], payload: CreateTaskIn) -> TaskOut:  # type: ignore[no-redef]
        return tool_create_task(user, payload)

    @agent.tool
    def get_task(ctx: RunContext[str], payload: GetTaskIn) -> TaskOut:  # type: ignore[no-redef]
        return tool_get_task(user, payload)

    @agent.tool
    def list_tasks(ctx: RunContext[str], payload: ListTasksIn) -> list[TaskOut]:  # type: ignore[no-redef]
        return tool_list_tasks(user, payload)

    @agent.tool
    def update_task(ctx: RunContext[str], payload: UpdateTaskIn) -> TaskOut:  # type: ignore[no-redef]
        return tool_update_task(user, payload)

    @agent.tool
    def delete_task(ctx: RunContext[str], payload: DeleteTaskIn) -> Dict[str, Any]:  # type: ignore[no-redef]
        return tool_delete_task(user, payload)

    # Project tools
    @agent.tool
    def create_project(ctx: RunContext[str], payload: CreateProjectIn) -> ProjectOut:  # type: ignore[no-redef]
        return tool_create_project(user, payload)

    @agent.tool
    def get_project(ctx: RunContext[str], payload: GetProjectIn) -> ProjectOut:  # type: ignore[no-redef]
        return tool_get_project(user, payload)

    @agent.tool
    def list_projects(ctx: RunContext[str], payload: ListProjectsIn) -> list[ProjectOut]:  # type: ignore[no-redef]
        return tool_list_projects(user, payload)

    @agent.tool
    def update_project(ctx: RunContext[str], payload: UpdateProjectIn) -> ProjectOut:  # type: ignore[no-redef]
        return tool_update_project(user, payload)

    @agent.tool
    def delete_project(ctx: RunContext[str], payload: DeleteProjectIn) -> Dict[str, Any]:  # type: ignore[no-redef]
        return tool_delete_project(user, payload)

    # Tag tools
    @agent.tool
    def create_tag(ctx: RunContext[str], payload: CreateTagIn) -> TagOut:  # type: ignore[no-redef]
        return tool_create_tag(user, payload)

    @agent.tool
    def get_tag(ctx: RunContext[str], payload: GetTagIn) -> TagOut:  # type: ignore[no-redef]
        return tool_get_tag(user, payload)

    @agent.tool
    def list_tags(ctx: RunContext[str], payload: ListTagsIn) -> list[TagOut]:  # type: ignore[no-redef]
        return tool_list_tags(user, payload)

    @agent.tool
    def update_tag(ctx: RunContext[str], payload: UpdateTagIn) -> TagOut:  # type: ignore[no-redef]
        return tool_update_tag(user, payload)

    @agent.tool
    def delete_tag(ctx: RunContext[str], payload: DeleteTagIn) -> Dict[str, Any]:  # type: ignore[no-redef]
        return tool_delete_tag(user, payload)

    # Comment tools
    @agent.tool
    def create_comment(ctx: RunContext[str], payload: CreateCommentIn) -> CommentOut:  # type: ignore[no-redef]
        return tool_create_comment(user, payload)

    @agent.tool
    def get_comment(ctx: RunContext[str], payload: GetCommentIn) -> CommentOut:  # type: ignore[no-redef]
        return tool_get_comment(user, payload)

    @agent.tool
    def list_comments(ctx: RunContext[str], payload: ListCommentsIn) -> list[CommentOut]:  # type: ignore[no-redef]
        return tool_list_comments(user, payload)

    @agent.tool
    def update_comment(ctx: RunContext[str], payload: UpdateCommentIn) -> CommentOut:  # type: ignore[no-redef]
        return tool_update_comment(user, payload)

    @agent.tool
    def delete_comment(ctx: RunContext[str], payload: DeleteCommentIn) -> Dict[str, Any]:  # type: ignore[no-redef]
        return tool_delete_comment(user, payload)

    return agent


def orm_agent_factory(user=None):
    """
    Create an agent that can directly use the django ORM
    :return: 
    :rtype: 
    """
    logfire.configure(token=settings.LOGFIRE_KEY)
    logfire.instrument_pydantic_ai()

    agent = Agent(
        model=model,
        name="Django ORM agent",
        system_prompt="""
        You have access to a Django ORM tool that allows you to interact with the database models. 
        The available models are:

        1. Project - for managing projects (fields: title, description, deadline, category, tags)
        2. Task - for managing tasks within projects (fields: title, description, project, assignees, depends_on, priority, status, due_date, estimated_hours, tags)
        3. Tag - for categorizing projects and tasks (fields: name, color)
        4. Comment - for adding comments to tasks (fields: title, description, task)
        
        You can perform the following operations:
        - Create new instances: Use orm_action with model_name and data
        - Read existing instances: Use orm_action with model_name and id
        - Update instances: Use orm_action with model_name, id and data
        - Delete instances: Use orm_action with model_name and id
        - Query instances: Use orm_action with model_name and optional filters
        
        Always specify the model_name in lowercase (e.g., "project", "task").
""",
        output_type=dict,
    )
    
    @agent.tool
    def orm_action(ctx: RunContext[str], action: Union[CreateAction, ReadAction, UpdateAction, DeleteAction, QueryAction]) -> Dict[str, Any]:
        """
        Execute a Django ORM action on a specified model.

        You can create, read, update, delete or query any of the allowed models:
        Project, Task, Tag, Comment.

        For create or update actions, provide the data as a dictionary.
        For read or delete actions, provide the id of the instance.
        For query actions, provide optional filters as a dictionary.

        Examples:
        - Create a new task: {"model_name": "task", "type": "create", "data": {"title": "New Task", "description": "...", "project_id": 1}}
        - Read a task: {"model_name": "task", "type": "read", "id": 1}
        - Update a task: {"model_name": "task", "type": "update", "id": 1, "data": {"status": "IN_PROGRESS"}}
        - Delete a task: {"model_name": "task", "type": "delete", "id": 1}
        - Query tasks: {"model_name": "task", "type": "query", "filters": {"project_id": 1}}
        """
        return tool_orm_action(user, action)

    return agent



def run_orm_agent(task):
    agent = orm_agent_factory()
    return agent.run_sync(task)
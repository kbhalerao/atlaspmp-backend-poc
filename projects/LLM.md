LLM Guide: Projects, Tasks, Tags, Comments APIs

Overview
- Base URL: /api/
- Auth: Django REST Framework (DRF). Assume an authenticated user for write operations.
- Models: Project, Task, Tag, Comment. Project/Task/Comment inherit owner, created, updated, llm_context.

General Concepts
- Ownership: Project, Task, Comment have an owner (CustomUser id). Many operations are scoped by owner.
- Permissions:
  - ProjectViewSet: list shows only projects owned by the current user (unless staff). Retrieve/update/delete require being the owner or staff (IsOwnerOrReadOnly).
  - TaskViewSet: non-staff can see tasks they own OR are assigned to. Write requires owner or staff.
  - CommentViewSet: non-staff sees own comments. Write requires owner or staff.
  - TagViewSet: authenticated users can CRUD tags.
- Relations by id: For relations (owner, project, assignees, depends_on, tags, task), pass integer IDs.

Models and Fields
1) Tag
- id (read-only), name (unique), color (e.g., "#000000").

2) Project
- id (read-only)
- title (string), description (string), owner (user id)
- created (read-only datetime), updated (read-only datetime)
- llm_context (JSON object; free-form for LLM usage)
- deadline (datetime, optional), category (string, optional)
- tags (list of Tag ids, optional)

3) Task
- id (read-only)
- title, description, owner (user id), project (project id)
- created, updated (read-only), llm_context (JSON)
- assignees (list of user ids)
- depends_on (task id, optional)
- priority (choices: LOW, MEDIUM, HIGH, URGENT; default MEDIUM)
- status (choices: TODO, IN_PROGRESS, REVIEW, DONE; default TODO)
- due_date (datetime, optional), estimated_hours (decimal, optional)
- tags (list of Tag ids, optional)

4) Comment
- id (read-only)
- title, description, owner (user id), task (task id)
- created, updated (read-only), llm_context (JSON)

Endpoints
Tags
- GET /api/tags/: list
- POST /api/tags/: create {name, color}
- GET /api/tags/{id}/: retrieve
- PATCH/PUT /api/tags/{id}/: update
- DELETE /api/tags/{id}/: delete

Projects
- GET /api/projects/: list only current user’s projects (unless staff)
- POST /api/projects/: create {title, description, owner, [deadline], [category], [tags]}
- GET /api/projects/{id}/: retrieve (403 if not owner and not staff)
- PATCH/PUT /api/projects/{id}/: update (owner or staff)
- DELETE /api/projects/{id}/: delete (owner or staff)

Tasks
- GET /api/tasks/: list tasks owned by current user or assigned to them (staff sees all)
- POST /api/tasks/: create {title, description, owner, project, [assignees], [depends_on], [priority], [status], [due_date], [estimated_hours], [tags]}
- GET /api/tasks/{id}/: retrieve (403 if not permitted by ownership/assignment rules)
- PATCH/PUT /api/tasks/{id}/: update (owner or staff)
- DELETE /api/tasks/{id}/: delete (owner or staff)

Comments
- GET /api/comments/: list only current user’s comments (staff sees all)
- POST /api/comments/: create {title, description, owner, task}
- GET /api/comments/{id}/: retrieve (403 if not owner and not staff)
- PATCH/PUT /api/comments/{id}/: update (owner or staff)
- DELETE /api/comments/{id}/: delete (owner or staff)

Status Codes
- 200 OK for successful GET/PUT/PATCH
- 201 Created for successful POST
- 204 No Content for successful DELETE
- 403 Forbidden when authenticated but not permitted
- 401 Unauthorized when not authenticated

Usage Examples
1) Create a Project
POST /api/projects/
{
  "title": "Soil Analysis",
  "description": "Analyze samples",
  "owner": 5,
  "category": "Research",
  "tags": [1, 2]
}
-> 201 Created with project object

2) Create a Task in a Project
POST /api/tasks/
{
  "title": "Prepare lab",
  "description": "Setup equipment",
  "owner": 5,
  "project": 10,
  "assignees": [5, 7],
  "priority": "HIGH",
  "status": "TODO"
}
-> 201 Created with task object

3) Add a Comment to a Task
POST /api/comments/
{
  "title": "Note",
  "description": "Initial setup complete",
  "owner": 7,
  "task": 22
}
-> 201 Created with comment object

4) List Tasks visible to current user
GET /api/tasks/
-> 200 OK with tasks owned by or assigned to the current user

LLM Safety & Guidance
- Always include correct integer IDs for relationships.
- Respect choice fields for Task.priority and Task.status; invalid values will fail validation.
- For lists, expect arrays. For detail endpoints, expect objects.
- Do not assume you can see or modify other users’ projects/tasks/comments unless staff.
- Use llm_context to store small, structured hints or state needed by the agent; keep it concise (e.g., {"next_action": "review"}).

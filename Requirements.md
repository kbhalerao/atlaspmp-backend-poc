# LLM Chat Single-Page View (SPV) — Product & Technical Requirements

## Goal

Build a single-page experience where an authenticated user can:
- Chat with an LLM-powered project management agent (backed by our existing Pydantic tools and DRF APIs).
- See and interact with a searchable, filterable task table that includes project and comment context.
- Select a specific object (task/project/comment) so the LLM has access to its full context and can act accordingly.
- Receive LLM-driven actions and, when changes are made, refresh the table to keep UI state in sync with the DB.

## Non-Goals (for now)
- Multi-page navigation or complex routing.
- Real-time streaming via websockets (can be added later). We start with simple polling or conditional refetch.
- Full-blown vector search. We will store llm_context for future RAG, but no embedding/vector DB is in scope for this iteration.

## Key Use Cases
- As a user, I can ask the agent to create tasks, assign users, change status, or summarize my work.
- As a user, I can search and filter tasks (by title, description, status, priority, project, tags, assignees).
- As a user, I can select a task (or project) to provide contextual grounding to the LLM so it can produce more accurate responses/actions.
- As a user, I can see when the agent has made changes (e.g., a task moved to DONE) and the table reflects that after a conditional refresh.
- As a supervisor, I can request a summary of activity and changes made
- As a supervisor, I can work with the agent to orchestrate pending tasks based on availability, priority and project status

# Frontend Requirements
1. Page Layout: 2 rows, with the first row having two columns.
   - Top Row, Left: LLM chat panel (message history, input box, send button).
   - Top Row, Right: Additional context window - shows selected object, or provides output artifacts from the LLM on a turn-by-turn basis. 
   - Bottom Row, Task table with search bar. Table shows columns: Task, Project, Priority, Status, Due, Assignees, Tags, Comments(#), Updated, and 'select' action button. 

2. Search & Filter
   - Server-backed paginated filters (query params) for status, priority, project_id, tag_id, assigned_to
   - For normal users, show only their own tasks. For superusers, show all tasks.
   - For superusers, show 'mine' filter to show only tasks assigned to the current user.
   - For superusers, show 'include_assigned' filter to show tasks assigned to other users.

3. Row Selection & Context
   - Selecting a row sets a current_context task object along with its project and comments. 
   - Snapshot contains essential fields and related info: for a task, include project info and last 2–3 comments; for a project, include basic details and recent tasks.
   - Context is passed to the LLM on next user message so that tools operate relative to this object (e.g., update this task).

4. Chat Panel
   - Messages rendered chronologically. Each assistant message may include a summary of actions taken and any errors.
   - Input box supports plain text. (Future: slash commands or tool quick-actions.)
   - A “Use current selection as context” toggle to explicitly include the selected object in the next request.
   - When the agent executes a write action (create/update/delete), set a flag to conditionally refetch the table.

5. Conditional Refresh Logic
   - After receiving an assistant response with an indication that data changed, perform a table refetch.
   - Heuristics: If response metadata indicates last_action in {'create','update','delete'} or if tool call name implies write, trigger refetch.
   - Alternatively, we can set up a websocket connection to receive signals from the backend to trigger refetches.

6. Error Handling & UX
   - Display friendly error messages when permissions fail (403) or inputs are invalid (400).
   - Show loading indicators during network calls.
   - Preserve chat history in component state for the session. (Future: persist per user/thread.)

Backend/API Requirements
1. Use Existing DRF Endpoints
   - /api/projects/, /api/tasks/, /api/comments/, /api/tags/ with current permission model.
   - Add search/filter query params for tasks (initial minimal):
     - q (icontains title/description), status, priority, project, tag, assigned (user id), mine (bool), include_assigned (bool).
   - If not already present, implement search/filter in TaskViewSet.get_queryset() based on query params but respecting permissions.

2. LLM Agent Invocation
   - Use projects.agent.agent_factory(user=request.user) to construct an agent bound to the current user.
   - Provide an endpoint to send a chat message:
     - POST /api/agent/chat
     - Body: { "message": str, "context": {"type": "task"|"project"|"none", "id": int|null }, "options": {"dry_run": bool=false} }
     - Behavior: The backend creates the agent, optionally fetches the context object and injects a concise context summary into the agent prompt, then runs the agent. If the agent uses tools that modify data, include metadata in the response.
     - Response: { "messages": [...], "tool_calls": [...], "result": any, "meta": {"changed": bool, "last_action": str|null} }

3. Context Injection Strategy
   - For task context, include: task fields, project title/id, tags, assignee emails, latest 2–3 comments (title + short description), and llm_context.
   - For project context: project fields, tags, last 3 tasks (id, title, status), and llm_context.
   - Keep context small (< 2 KB target) and structured for consistent LLM consumption.

4. LLM Safety & Permissions
   - Agent tools already enforce object-level permissions. Backend must ensure the agent is created with the actual request.user.
   - Do not allow the LLM to set owners arbitrarily; use tool restrictions already in place.

5. Table Data Endpoint(s)
   - Prefer using existing /api/tasks/ with added filters. The frontend can drive filtering via query params:
     - GET /api/tasks/?q=soil&status=IN_PROGRESS&project=3&tag=urgent&assigned=5&mine=true&include_assigned=true
   - Ensure comments count is efficiently included (option A: annotate with Count; option B: separate fetch for selected rows). Start with simple fetch; optimize later.

6. Eventing for Conditional Refresh
   - The chat response includes meta.changed flag and last_action. The frontend uses this to refetch tasks.

Data Model Notes
- llm_context JSON field is available across Project, Task, Comment. Use it to store compact traces of agent actions and key hints (e.g., {"source":"agent","last_action":"update","actor_user_id":7,"summary_text":"Marked done"}).
- Future RAG: We can add a searchable text field (e.g., llm_text) or a basic embedding service; not in scope now.

Security & Auth
- Session or token auth via DRF. All endpoints continue to enforce existing permissions.
- Avoid exposing sensitive fields; in agent/chat response, include only necessary traces and tool metadata.

Testing Requirements
- Backend tests for new /api/agent/chat endpoint: permission binding to user, context injection correctness, and meta.changed flag behavior.
- Backend tests for TaskViewSet query filters (q, status, priority, project, tag, assigned, mine, include_assigned).
- Frontend tests (if/when added later): table filtering behavior and conditional refetch after chat action.

Open Questions
1. Authentication method for the SPV: Session is fine for now. 
2. Should we support streaming responses for the assistant? Yes
3. Do we need pagination/sorting on the server now, or can we defer? - no add right away
4. How should we persist chat history (per user, per project, per task)? DB model needed? - no - just in memory. Chat history can be summarized into the llm_context window for traceability. 
5. What is the maximum context size we can safely include in each chat turn? 10k tokens. 
6. Should the agent be allowed to create projects on behalf of other users if the caller is staff? (Currently yes; confirm.) Yes. 
7. Do we need optimistic UI updates, or is post-action refetch sufficient for the first version? Post action refetch.
8. Any UI framework preference for the SPV (React/Vue/HTMX/Django template + Alpine)? Let's maximize django templates and use HTML + Alpine for reactivity. 

MVP Delivery Checklist
- [ ] TaskViewSet supports q/status/priority/project/tag/assigned/mine/include_assigned filters.
- [ ] New POST /api/agent/chat endpoint returning messages, tool_calls, and meta.changed.
- [ ] Minimal UI mockup (template or static HTML/JS) wired to the chat endpoint and tasks list.
- [ ] Tests for chat endpoint and task filters.

Notes for Iteration
- Start with backend primitives (filters + chat endpoint). UI can be a basic template in templates/ with vanilla JS to prove the flow.
- After MVP works, consider promoting to a proper SPA with a frontend framework.

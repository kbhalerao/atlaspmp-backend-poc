LLM Guide: Users API

Overview
- Base URL: /api/
- This project uses Django REST Framework (DRF).
- Authentication: Assume session auth during tests; in production, use DRF authentication (e.g., token/session). For safety, include credentials if required.
- Primary model: users.CustomUser (email is the unique identifier; no username field).

Important Rules
- Only admins (is_staff=True) can list all users, create new users, or delete users.
- A non-admin user can retrieve or update only their own user object (object-level permission: IsAdminOrSelf).
- Passwords are write-only in the API. Never echo passwords back.

Fields (CustomUser)
- id: integer (read-only)
- email: string (unique, required)
- password: string (write-only; optional on update)
- first_name: string
- last_name: string
- is_staff: boolean (admin-only to set)
- is_active: boolean
- date_joined: datetime (read-only)

Endpoints
- GET /api/users/ (admin only): list users.
- POST /api/users/ (admin only): create a user.
- GET /api/users/{id}/ (self or admin): retrieve a user.
- PATCH /api/users/{id}/ (self or admin): partial update a user.
- PUT /api/users/{id}/ (self or admin): full update a user.
- DELETE /api/users/{id}/ (admin only): delete a user.

Status Codes & Permissions
- 200 OK: successful GET/PUT/PATCH.
- 201 Created: successful POST.
- 204 No Content: successful DELETE.
- 403 Forbidden: authenticated but not allowed (e.g., non-admin trying to list, or access another user).
- 401 Unauthorized: not authenticated.

Examples
1) Admin lists users
- Request: GET /api/users/
- Expected: 200 OK, array of user objects (without password).

2) Admin creates user
- Request: POST /api/users/
  {
    "email": "new@example.com",
    "password": "StrongPass123",
    "first_name": "New",
    "last_name": "User",
    "is_active": true
  }
- Response: 201 Created with user object (no password). Password is hashed server-side.

3) User retrieves self
- Request (as user id=5): GET /api/users/5/
- Response: 200 OK with user object.

4) User fails to retrieve different user
- Request (as user id=5): GET /api/users/1/
- Response: 403 Forbidden.

Notes for LLMs
- Always determine the current user’s id before building self-targeted requests if needed.
- Do not attempt to include a username field; it does not exist.
- When updating the password, send only in the request body; never store or log it. After updating, consider re-authentication as tokens/sessions may change.
- Treat email as the login identifier.

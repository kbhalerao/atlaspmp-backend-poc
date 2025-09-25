# Atlas Project Management Backend

Atlas is an AI-powered project management system that leverages Large Language Models (LLMs) to automate and enhance
project management workflows. Built with Django and SQLite, it provides a robust API for managing projects, tasks, and
team collaboration.

## Setup

1. Clone the repository
2. Install dependencies with `uv sync && uv install`
3. Run migrations with `python manage.py migrate` or `uv migrate`
4. Create a superuser with `python manage.py createsuperuser` 
5. Start the development server with `python manage.py runserver`
6. Create a `.env` file in the root directory - see `env.example` for list of environment variables

## Features

- **AI-Driven Project Management**: Automated task breakdown, assignment, and tracking
- **Natural Language Interface**: Interact with your projects using plain English
- **RESTful API**: Complete API for integration with frontend applications
- **Role-Based Access Control**: Secure user management and authentication
- **Real-time Updates**: Track project progress and team activities

## Data Models

### User

- Custom user model with email authentication
- Fields: email, first_name, last_name, is_active, is_staff
- Manages user authentication and permissions

### Project

- Central entity for organizing work
- Fields: title, description, owner, deadline, category, tags
- Tracks project metadata and progress

### Task

- Individual work items within projects
- Fields: title, description, owner, project, assignees, status, priority, due_date
- Supports task dependencies and time tracking

### Tag

- Flexible categorization system
- Fields: name, color
- Used to organize both projects and tasks

### Comment

- Communication and documentation
- Fields: title, description, owner, task
- Enables team discussion and progress updates

## Example Natural Language Queries

- **Create a new project**
- **Create a new task**
- **Assign a task to a team member**
- **Update a task's status**
- **Update a task's due date**
- **Add a comment to a task**
- **Add a tag to a project or task**
- **List all projects**
- **List all tasks**
- **List all tasks assigned to a team member**

## Agent architecture   

Atlas uses a single-agent architecture to interact with the LLM. The agent is responsible for:
- Generating natural language queries from user input
- Generating responses from the LLM
- Handling errors and exceptions



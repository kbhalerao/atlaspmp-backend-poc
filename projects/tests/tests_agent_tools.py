from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone

from projects.models import Project, Task
from projects.agent.tools.task import (
    CreateTaskIn, UpdateTaskIn, GetTaskIn, ListTasksIn, DeleteTaskIn,
    tool_create_task, tool_get_task, tool_list_tasks, tool_update_task, tool_delete_task,
)
from projects.agent.tools.project import (
    CreateProjectIn, UpdateProjectIn, GetProjectIn, ListProjectsIn, DeleteProjectIn,
    tool_create_project, tool_get_project, tool_list_projects, tool_update_project, tool_delete_project,
)
from projects.agent.tools.tag import (
    CreateTagIn, UpdateTagIn, GetTagIn, ListTagsIn, DeleteTagIn,
    tool_create_tag, tool_get_tag, tool_list_tags, tool_update_tag, tool_delete_tag,
)
from projects.agent.tools.comment import (
    CreateCommentIn, UpdateCommentIn, GetCommentIn, ListCommentsIn, DeleteCommentIn,
    tool_create_comment, tool_get_comment, tool_list_comments, tool_update_comment, tool_delete_comment,
)


class AgentToolsTaskTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.User = User
        self.owner = User.objects.create_user(email='owner@example.com', password='pass')
        self.other = User.objects.create_user(email='other@example.com', password='pass')
        self.admin = User.objects.create_superuser(email='admin@example.com', password='pass')
        self.project = Project.objects.create(title='P', description='d', owner=self.owner)

    def test_create_get_update_delete_flow(self):
        payload = CreateTaskIn(title='T1', description='desc', project_id=self.project.id, llm_notes='initial note')
        out = tool_create_task(self.owner, payload)
        self.assertEqual(out.title, 'T1')
        self.assertEqual(out.owner_id, self.owner.id)  # owner is project owner
        self.assertIn('source', out.llm_context)
        tid = out.id

        # other non-staff cannot view if not assigned and not owner
        with self.assertRaises(PermissionError):
            tool_get_task(self.other, GetTaskIn(task_id=tid))

        # owner can update
        upd = UpdateTaskIn(task_id=tid, status='IN_PROGRESS', llm_notes='progressing')
        out2 = tool_update_task(self.owner, upd)
        self.assertEqual(out2.status, 'IN_PROGRESS')
        self.assertEqual(out2.llm_context.get('last_action'), 'update')

        # list tasks for owner includes this task
        lst = tool_list_tasks(self.owner, ListTasksIn())
        self.assertTrue(any(t.id == tid for t in lst))

        # admin can delete
        res = tool_delete_task(self.admin, DeleteTaskIn(task_id=tid))
        self.assertTrue(res['deleted'])
        self.assertFalse(Task.objects.filter(id=tid).exists())

    def test_permission_create_requires_project_owner_or_staff(self):
        # other user cannot create in a project they don't own
        with self.assertRaises(PermissionError):
            tool_create_task(self.other, CreateTaskIn(title='X', description='d', project_id=self.project.id))
        # admin can create
        out = tool_create_task(self.admin, CreateTaskIn(title='Y', description='d', project_id=self.project.id))
        self.assertEqual(out.project_id, self.project.id)

    def test_project_and_tag_and_comment_tools(self):
        # Tags
        tag1 = tool_create_tag(self.owner, CreateTagIn(name='soil', color='#123456'))
        tag2 = tool_create_tag(self.owner, CreateTagIn(name='lab', color='#654321'))
        tags = tool_list_tags(self.owner, ListTagsIn())
        self.assertTrue(any(t.id == tag1.id for t in tags))
        # Update a tag
        tag1u = tool_update_tag(self.owner, UpdateTagIn(tag_id=tag1.id, color='#000000'))
        self.assertEqual(tag1u.color, '#000000')

        # Projects
        # Non-staff cannot create project for others
        with self.assertRaises(PermissionError):
            tool_create_project(self.other, CreateProjectIn(title='Other P', description='d', owner_id=self.owner.id))
        proj_out = tool_create_project(self.owner, CreateProjectIn(title='My P', description='d', owner_id=self.owner.id, tag_ids=[tag1.id, tag2.id]))
        self.assertEqual(proj_out.owner_id, self.owner.id)
        # Get/list projects
        fetched = tool_get_project(self.owner, GetProjectIn(project_id=proj_out.id))
        self.assertEqual(fetched.id, proj_out.id)
        my_projects = tool_list_projects(self.owner, ListProjectsIn())
        self.assertTrue(any(p.id == proj_out.id for p in my_projects))
        # Update
        proj_out2 = tool_update_project(self.owner, UpdateProjectIn(project_id=proj_out.id, category='Research'))
        self.assertEqual(proj_out2.category, 'Research')

        # Comments on task
        task_out = tool_create_task(self.owner, CreateTaskIn(title='Comment here', description='td', project_id=self.project.id))
        # other not assigned cannot comment
        with self.assertRaises(PermissionError):
            tool_create_comment(self.other, CreateCommentIn(title='no', description='x', task_id=task_out.id))
        # owner can comment
        com_out = tool_create_comment(self.owner, CreateCommentIn(title='note', description='ok', task_id=task_out.id))
        self.assertEqual(com_out.owner_id, self.owner.id)
        com_list = tool_list_comments(self.owner, ListCommentsIn(task_id=task_out.id))
        self.assertTrue(any(c.id == com_out.id for c in com_list))
        # update and delete
        com_out2 = tool_update_comment(self.owner, UpdateCommentIn(comment_id=com_out.id, description='updated'))
        self.assertEqual(com_out2.description, 'updated')
        res = tool_delete_comment(self.owner, DeleteCommentIn(comment_id=com_out.id))
        self.assertTrue(res['deleted'])

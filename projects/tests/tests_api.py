from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase, APIClient
from rest_framework import status

from projects.models import Project, Task, Tag, Comment


class ProjectsAPITests(APITestCase):
    def setUp(self):
        self.User = get_user_model()
        self.owner = self.User.objects.create_user(email='owner@example.com', password='pass1234')
        self.other = self.User.objects.create_user(email='other@example.com', password='pass1234')
        self.client = APIClient()
        self.client.force_authenticate(user=self.owner)

    def test_tag_crud(self):
        resp = self.client.post('/api/tags/', {'name': 'urgent', 'color': '#ff0000'}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        tag_id = resp.data['id']
        resp = self.client.get('/api/tags/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        resp = self.client.patch(f'/api/tags/{tag_id}/', {'color': '#00ff00'}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        resp = self.client.delete(f'/api/tags/{tag_id}/')
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)

    def test_project_crud_and_scope(self):
        # create project owned by owner
        payload = {'title': 'P1', 'description': 'd', 'owner_id': self.owner.id}
        resp = self.client.post('/api/projects/', payload, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        proj_id = resp.data['id']
        # list returns only own projects
        resp = self.client.get('/api/projects/')
        # paginated response
        self.assertEqual(resp.data.get('count'), 1)
        # other user cannot see owner's project
        self.client.force_authenticate(user=self.other)
        resp = self.client.get('/api/projects/')
        self.assertEqual(resp.data.get('count'), 0)
        # other cannot update owner's project
        resp = self.client.patch(f'/api/projects/{proj_id}/', {'title': 'X'}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_task_and_comment_crud(self):
        # create project
        p = Project.objects.create(title='P', description='d', owner=self.owner)
        # create task
        task_payload = {
            'title': 'T1', 'description': 'td', 'owner_id': self.owner.id, 'project_id': p.id,
            'assignees': [self.owner.id], 'priority': 'HIGH', 'status': 'TODO'
        }
        resp = self.client.post('/api/tasks/', task_payload, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        task_id = resp.data['id']
        # list tasks returns at least this task
        resp = self.client.get('/api/tasks/')
        results = resp.data.get('results', resp.data)
        self.assertTrue(any(t['id'] == task_id for t in results))
        # comment
        comment_payload = {'title': 'Note', 'description': 'ok', 'owner': self.owner.id, 'task': task_id}
        resp = self.client.post('/api/comments/', comment_payload, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        comment_id = resp.data['id']
        # update task status
        resp = self.client.patch(f'/api/tasks/{task_id}/', {'status': 'IN_PROGRESS'}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        # delete comment
        resp = self.client.delete(f'/api/comments/{comment_id}/')
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)

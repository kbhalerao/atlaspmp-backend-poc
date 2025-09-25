from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase, APIClient
from rest_framework import status

from projects.models import Project, Task, Tag


class TaskFiltersAPITests(APITestCase):
    def setUp(self):
        User = get_user_model()
        self.owner = User.objects.create_user(email='owner@example.com', password='pass')
        self.assignee = User.objects.create_user(email='assignee@example.com', password='pass')
        self.other = User.objects.create_user(email='other@example.com', password='pass')
        self.admin = User.objects.create_superuser(email='admin@example.com', password='pass')

        self.p1 = Project.objects.create(title='Proj A', description='A', owner=self.owner)
        self.p2 = Project.objects.create(title='Proj B', description='B', owner=self.other)

        self.tag_soil = Tag.objects.create(name='soil', color='#111111')
        self.tag_lab = Tag.objects.create(name='lab', color='#222222')

        # Tasks for owner
        self.t1 = Task.objects.create(title='Collect soil north', description='field work', owner=self.owner, project=self.p1, priority='HIGH', status='TODO')
        self.t1.tags.add(self.tag_soil)
        self.t1.assignees.add(self.owner)

        self.t2 = Task.objects.create(title='Analyze lab samples', description='lab bench', owner=self.owner, project=self.p1, priority='MEDIUM', status='IN_PROGRESS')
        self.t2.tags.add(self.tag_lab)
        self.t2.assignees.add(self.assignee)

        # Task owned by other but assigned to owner
        self.t3 = Task.objects.create(title='External task', description='assigned in', owner=self.other, project=self.p2, priority='LOW', status='REVIEW')
        self.t3.assignees.add(self.owner)

        # Task not visible to owner
        self.t4 = Task.objects.create(title='Other hidden', description='hidden', owner=self.other, project=self.p2, priority='URGENT', status='DONE')

        self.client = APIClient()

    def _results(self, resp):
        return resp.data.get('results', resp.data)

    def test_visibility_scoping(self):
        self.client.force_authenticate(user=self.owner)
        resp = self.client.get('/api/tasks/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        ids = {t['id'] for t in self._results(resp)}
        # Should include t1 (owned), t2 (owned), t3 (assigned), not t4
        self.assertTrue(self.t1.id in ids and self.t2.id in ids and self.t3.id in ids)
        self.assertFalse(self.t4.id in ids)

    def test_q_filter(self):
        self.client.force_authenticate(user=self.owner)
        resp = self.client.get('/api/tasks/?q=soil')
        ids = {t['id'] for t in self._results(resp)}
        self.assertIn(self.t1.id, ids)
        self.assertNotIn(self.t2.id, ids)

    def test_status_priority_project_filters(self):
        self.client.force_authenticate(user=self.owner)
        # status
        resp = self.client.get('/api/tasks/?status=IN_PROGRESS')
        ids = {t['id'] for t in self._results(resp)}
        self.assertIn(self.t2.id, ids)
        self.assertNotIn(self.t1.id, ids)
        # priority
        resp = self.client.get('/api/tasks/?priority=LOW')
        ids = {t['id'] for t in self._results(resp)}
        self.assertIn(self.t3.id, ids)
        self.assertNotIn(self.t1.id, ids)
        # project
        resp = self.client.get(f'/api/tasks/?project={self.p1.id}')
        ids = {t['id'] for t in self._results(resp)}
        self.assertIn(self.t1.id, ids)
        self.assertIn(self.t2.id, ids)
        self.assertNotIn(self.t3.id, ids)

    def test_tag_filter_by_id_and_name(self):
        self.client.force_authenticate(user=self.owner)
        # by id
        resp = self.client.get(f'/api/tasks/?tag={self.tag_soil.id}')
        ids = {t['id'] for t in self._results(resp)}
        self.assertIn(self.t1.id, ids)
        self.assertNotIn(self.t2.id, ids)
        # by name
        resp = self.client.get('/api/tasks/?tag=lab')
        ids = {t['id'] for t in self._results(resp)}
        self.assertIn(self.t2.id, ids)
        self.assertNotIn(self.t1.id, ids)

    def test_assigned_and_mine_and_include_assigned(self):
        self.client.force_authenticate(user=self.owner)
        # assigned to self.owner
        resp = self.client.get(f'/api/tasks/?assigned={self.owner.id}')
        ids = {t['id'] for t in self._results(resp)}
        self.assertIn(self.t1.id, ids)
        self.assertIn(self.t3.id, ids)
        # mine only
        resp = self.client.get('/api/tasks/?mine=true')
        ids = {t['id'] for t in self._results(resp)}
        self.assertIn(self.t1.id, ids)
        self.assertIn(self.t2.id, ids)
        self.assertNotIn(self.t3.id, ids)
        # exclude assigned (owner-only)
        resp = self.client.get('/api/tasks/?include_assigned=false')
        ids = {t['id'] for t in self._results(resp)}
        self.assertIn(self.t1.id, ids)
        self.assertIn(self.t2.id, ids)
        self.assertNotIn(self.t3.id, ids)

    def test_ordering_and_pagination(self):
        self.client.force_authenticate(user=self.owner)
        resp = self.client.get('/api/tasks/?ordering=-priority')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        # ensure paginated structure exists
        self.assertIn('results', resp.data)

        # Admin sees all tasks
        self.client.force_authenticate(user=self.admin)
        resp = self.client.get('/api/tasks/?mine=true')
        # mine=true for admin should filter to admin-owned, which is none here
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        results = resp.data.get('results', resp.data)
        self.assertEqual(len(results), 0)

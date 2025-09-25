from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase, APIClient
from rest_framework import status

from projects.models import Project, Task


class AgentChatApiTests(APITestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(email='u@example.com', password='pass')
        self.other = User.objects.create_user(email='o@example.com', password='pass')
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

        self.project = Project.objects.create(title='P', description='d', owner=self.user)
        self.task = Task.objects.create(title='T', description='d', owner=self.user, project=self.project)

    def test_post_agent_chat_with_context_echo_and_meta(self):
        payload = {
            'message': 'please update',
            'context': {'type': 'task', 'id': self.task.id},
            'options': {'simulate_change': True, 'last_action': 'update'}
        }
        resp = self.client.post('/api/agent/chat', payload, format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        body = resp.data
        self.assertIn('messages', body)
        self.assertIn('meta', body)
        self.assertEqual(body['meta']['user_id'], self.user.id)
        self.assertTrue(body['meta']['changed'])
        self.assertEqual(body['meta']['last_action'], 'update')
        # context echoed
        self.assertEqual(body['result']['context']['type'], 'task')
        self.assertEqual(body['result']['context']['id'], self.task.id)

    def test_post_agent_chat_project_context(self):
        payload = {
            'message': 'summarize',
            'context': {'type': 'project', 'id': self.project.id},
            'options': {'simulate_change': False}
        }
        resp = self.client.post('/api/agent/chat', payload, format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        ctx = resp.data['result']['context']
        self.assertEqual(ctx['type'], 'project')
        self.assertEqual(ctx['id'], self.project.id)
        self.assertFalse(resp.data['meta']['changed'])

    def test_sse_stream_endpoint(self):
        resp = self.client.get('/api/agent/chat/stream')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.get('Content-Type'), 'text/event-stream')
        content = b''.join(resp.streaming_content)
        text = content.decode('utf-8')
        # basic SSE structure
        self.assertIn('event: hello', text)
        self.assertIn('event: done', text)

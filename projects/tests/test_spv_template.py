from django.contrib.auth import get_user_model
from django.test import TestCase


class SpvTemplateTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(email='spv@example.com', password='pass')

    def test_spv_requires_auth_and_renders(self):
        # unauthenticated should redirect to login (302) or 302 to login page depending on config
        resp = self.client.get('/spv/')
        self.assertIn(resp.status_code, [302, 301])
        # login
        self.client.force_login(self.user)
        resp = self.client.get('/spv/')
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Atlas PMP Mini PoC')
        self.assertContains(resp, 'Tasks')

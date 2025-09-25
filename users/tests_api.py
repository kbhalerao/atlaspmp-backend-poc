from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase, APIClient
from rest_framework import status


class UsersAPITests(APITestCase):
    def setUp(self):
        self.User = get_user_model()
        self.admin = self.User.objects.create_superuser(email='admin@example.com', password='adminpass')
        self.user = self.User.objects.create_user(email='user1@example.com', password='pass1234', first_name='U1')
        self.client = APIClient()

    def test_admin_can_list_and_create_users(self):
        self.client.force_authenticate(user=self.admin)
        # list
        resp = self.client.get('/api/users/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        # create
        payload = {
            'email': 'new@example.com',
            'password': 'newpass',
            'first_name': 'New',
            'last_name': 'User',
            'is_active': True,
        }
        resp = self.client.post('/api/users/', payload, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        uid = resp.data['id']
        # password should be hashed
        created = self.User.objects.get(id=uid)
        self.assertTrue(created.check_password('newpass'))

    def test_user_can_retrieve_and_update_self_but_not_others(self):
        self.client.force_authenticate(user=self.user)
        # retrieve self
        resp = self.client.get(f'/api/users/{self.user.id}/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        # update self
        resp = self.client.patch(f'/api/users/{self.user.id}/', {'first_name': 'Updated'}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        # cannot list (admin only)
        resp = self.client.get('/api/users/')
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)
        # cannot access others
        resp = self.client.get(f'/api/users/{self.admin.id}/')
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

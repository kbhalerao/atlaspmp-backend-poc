from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError


class CustomUserTests(TestCase):
    def setUp(self):
        self.User = get_user_model()

    def test_create_user(self):
        user = self.User.objects.create_user(
            email='normal@user.com',
            password='foo'
        )
        self.assertEqual(user.email, 'normal@user.com')
        self.assertTrue(user.is_active)
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertIsNone(user.username)

    def test_create_superuser(self):
        admin_user = self.User.objects.create_superuser(
            email='super@user.com',
            password='foo'
        )
        self.assertEqual(admin_user.email, 'super@user.com')
        self.assertTrue(admin_user.is_active)
        self.assertTrue(admin_user.is_staff)
        self.assertTrue(admin_user.is_superuser)
        self.assertIsNone(admin_user.username)

    def test_email_normalize(self):
        email = 'test@EXAMPLE.com'
        user = self.User.objects.create_user(email=email, password='foo')
        self.assertEqual(user.email, email.lower())

    def test_create_user_without_email(self):
        with self.assertRaises(ValueError):
            self.User.objects.create_user(email='', password='foo')

    def test_create_user_with_invalid_email(self):
        with self.assertRaises(ValidationError):
            user = self.User.objects.create_user(
                email='notanemail',
                password='foo'
            )
            user.full_clean()

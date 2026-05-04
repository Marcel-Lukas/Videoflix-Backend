"""Tests for ``LoginView``."""

from django.test import override_settings
from django.urls import reverse

from rest_framework import status
from rest_framework.test import APITestCase

from .helpers import TEST_EMAIL, TEST_PASSWORD, TEST_SETTINGS, make_user


@override_settings(**TEST_SETTINGS)
class LoginViewTests(APITestCase):
    """Tests for ``POST /api/login/``."""

    url = reverse('login')

    def setUp(self):
        self.user = make_user()

    def test_login_success_sets_cookies(self):
        response = self.client.post(
            self.url,
            {'email': TEST_EMAIL, 'password': TEST_PASSWORD},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['detail'], 'Login successful')
        self.assertEqual(response.data['user']['username'], TEST_EMAIL)
        self.assertIn('access_token', response.cookies)
        self.assertIn('refresh_token', response.cookies)
        self.assertTrue(response.cookies['access_token']['httponly'])

    def test_login_wrong_password(self):
        response = self.client.post(
            self.url,
            {'email': TEST_EMAIL, 'password': 'wrong-password'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertNotIn('access_token', response.cookies)

    def test_login_unknown_email(self):
        response = self.client.post(
            self.url,
            {'email': 'unknown@example.com', 'password': TEST_PASSWORD},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_login_inactive_user(self):
        self.user.is_active = False
        self.user.save()

        response = self.client.post(
            self.url,
            {'email': TEST_EMAIL, 'password': TEST_PASSWORD},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

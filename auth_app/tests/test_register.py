"""Tests for ``RegisterView``."""

from unittest.mock import patch

from django.test import override_settings
from django.urls import reverse

from rest_framework import status
from rest_framework.test import APITestCase

from .helpers import TEST_EMAIL, TEST_PASSWORD, TEST_SETTINGS, User, make_user


@override_settings(**TEST_SETTINGS)
class RegisterViewTests(APITestCase):
    """Tests for ``POST /api/register/``."""

    url = reverse('register')

    @patch('auth_app.api.views.django_rq.enqueue')
    def test_register_success(self, mocked_enqueue):
        payload = {
            'email': TEST_EMAIL,
            'password': TEST_PASSWORD,
            'confirmed_password': TEST_PASSWORD,
        }

        response = self.client.post(self.url, payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['user']['email'], TEST_EMAIL)
        self.assertNotIn('token', response.data)

        user = User.objects.get(email=TEST_EMAIL)
        self.assertFalse(user.is_active)
        mocked_enqueue.assert_called_once()

    @patch('auth_app.api.views.django_rq.enqueue')
    def test_register_password_mismatch(self, mocked_enqueue):
        payload = {
            'email': TEST_EMAIL,
            'password': TEST_PASSWORD,
            'confirmed_password': 'different',
        }

        response = self.client.post(self.url, payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('confirmed_password', response.data)
        self.assertFalse(User.objects.filter(email=TEST_EMAIL).exists())
        mocked_enqueue.assert_not_called()

    @patch('auth_app.api.views.django_rq.enqueue')
    def test_register_email_already_exists(self, mocked_enqueue):
        make_user()
        payload = {
            'email': TEST_EMAIL,
            'password': TEST_PASSWORD,
            'confirmed_password': TEST_PASSWORD,
        }

        response = self.client.post(self.url, payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('email', response.data)
        mocked_enqueue.assert_not_called()

    def test_register_missing_email(self):
        payload = {
            'password': TEST_PASSWORD,
            'confirmed_password': TEST_PASSWORD,
        }

        response = self.client.post(self.url, payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('email', response.data)

"""Tests for ``ActivateAccountView``."""

from django.contrib.auth.tokens import default_token_generator
from django.test import override_settings
from django.urls import reverse

from rest_framework import status
from rest_framework.test import APITestCase

from .helpers import TEST_SETTINGS, encode_uid, make_user


@override_settings(**TEST_SETTINGS)
class ActivateAccountViewTests(APITestCase):
    """Tests for ``GET /api/activate/<uidb64>/<token>/``."""

    def setUp(self):
        self.user = make_user(is_active=False)
        self.uidb64 = encode_uid(self.user)
        self.token = default_token_generator.make_token(self.user)

    def test_activate_success(self):
        url = reverse('activate', kwargs={'uidb64': self.uidb64, 'token': self.token})

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_active)

    def test_activate_invalid_token(self):
        url = reverse(
            'activate', kwargs={'uidb64': self.uidb64, 'token': 'invalid-token'}
        )

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_active)

    def test_activate_invalid_uid(self):
        url = reverse('activate', kwargs={'uidb64': 'invalid', 'token': self.token})

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

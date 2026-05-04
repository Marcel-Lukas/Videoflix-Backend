"""Tests for ``PasswordResetRequestView`` and ``PasswordResetConfirmView``."""

from unittest.mock import patch

from django.contrib.auth.tokens import default_token_generator
from django.test import override_settings
from django.urls import reverse

from rest_framework import status
from rest_framework.test import APITestCase

from .helpers import TEST_EMAIL, TEST_SETTINGS, encode_uid, make_user


@override_settings(**TEST_SETTINGS)
class PasswordResetRequestViewTests(APITestCase):
    """Tests for ``POST /api/password_reset/``."""

    url = reverse('password_reset')

    def setUp(self):
        self.user = make_user()

    @patch('auth_app.api.views.django_rq.enqueue')
    def test_request_for_existing_user_enqueues_mail(self, mocked_enqueue):
        response = self.client.post(self.url, {'email': TEST_EMAIL}, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mocked_enqueue.assert_called_once()

    @patch('auth_app.api.views.django_rq.enqueue')
    def test_request_for_unknown_user_returns_200_without_enqueue(self, mocked_enqueue):
        response = self.client.post(
            self.url, {'email': 'unknown@example.com'}, format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mocked_enqueue.assert_not_called()

    @patch('auth_app.api.views.django_rq.enqueue')
    def test_request_for_inactive_user_does_not_enqueue(self, mocked_enqueue):
        self.user.is_active = False
        self.user.save()

        response = self.client.post(self.url, {'email': TEST_EMAIL}, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mocked_enqueue.assert_not_called()

    def test_request_invalid_email(self):
        response = self.client.post(self.url, {'email': 'not-an-email'}, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


@override_settings(**TEST_SETTINGS)
class PasswordResetConfirmViewTests(APITestCase):
    """Tests for ``POST /api/password_confirm/<uidb64>/<token>/``."""

    new_password = 'BrandNewPass!234'

    def setUp(self):
        self.user = make_user()
        self.uidb64 = encode_uid(self.user)
        self.token = default_token_generator.make_token(self.user)

    def _url(self, uidb64=None, token=None):
        return reverse(
            'password_reset_confirm',
            kwargs={
                'uidb64': uidb64 or self.uidb64,
                'token': token or self.token,
            },
        )

    def test_confirm_success_changes_password(self):
        response = self.client.post(
            self._url(),
            {
                'new_password': self.new_password,
                'confirm_password': self.new_password,
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(self.new_password))

    def test_confirm_password_mismatch(self):
        response = self.client.post(
            self._url(),
            {
                'new_password': self.new_password,
                'confirm_password': 'different-password',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.user.refresh_from_db()
        self.assertFalse(self.user.check_password(self.new_password))

    def test_confirm_invalid_token(self):
        response = self.client.post(
            self._url(token='invalid-token'),
            {
                'new_password': self.new_password,
                'confirm_password': self.new_password,
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_confirm_invalid_uid(self):
        response = self.client.post(
            self._url(uidb64='invalid'),
            {
                'new_password': self.new_password,
                'confirm_password': self.new_password,
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_confirm_weak_password_rejected(self):
        response = self.client.post(
            self._url(),
            {'new_password': '12345678', 'confirm_password': '12345678'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('new_password', response.data)

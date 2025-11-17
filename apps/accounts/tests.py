from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import User


class UserModelTest(TestCase):
    """Test User model functionality."""

    def setUp(self):
        self.user = User.objects.create_user(
            email="test@example.com",
            password="testpass123",
            first_name="Test",
            last_name="User",
        )

    def test_user_creation(self):
        """Test user creation with email as username."""
        self.assertEqual(self.user.email, "test@example.com")
        self.assertEqual(self.user.get_full_name(), "Test User")
        self.assertTrue(self.user.check_password("testpass123"))

    def test_user_str(self):
        """Test user string representation."""
        self.assertEqual(str(self.user), "Test User")

    def test_online_status(self):
        """Test online/offline status methods."""
        self.assertFalse(self.user.is_online)

        self.user.set_online()
        self.assertTrue(self.user.is_online)
        self.assertIsNone(self.user.last_seen)

        self.user.set_offline()
        self.assertFalse(self.user.is_online)
        self.assertIsNotNone(self.user.last_seen)


class AuthenticationAPITest(APITestCase):
    """Test authentication API endpoints."""

    def setUp(self):
        self.user_data = {
            "email": "test@example.com",
            "password": "testpass123",
            "first_name": "Test",
            "last_name": "User",
        }
        self.user = User.objects.create_user(**self.user_data)

    def test_register(self):
        """Test user registration."""
        data = {
            "email": "newuser@example.com",
            "password": "newpass123",
            "password_confirm": "newpass123",
            "first_name": "New",
            "last_name": "User",
        }

        response = self.client.post(reverse("accounts:register"), data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("user", response.data)
        self.assertIn("tokens", response.data)

    def test_login(self):
        """Test user login."""
        data = {
            "email": self.user_data["email"],
            "password": self.user_data["password"],
        }

        response = self.client.post(reverse("accounts:login"), data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("user", response.data)
        self.assertIn("tokens", response.data)

    def test_profile_update(self):
        """Test profile update."""
        self.client.force_authenticate(user=self.user)

        data = {"first_name": "Updated", "bio": "Updated bio"}

        response = self.client.patch(reverse("accounts:profile"), data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["first_name"], "Updated")
        self.assertEqual(response.data["bio"], "Updated bio")

    def test_change_password(self):
        """Test password change."""
        self.client.force_authenticate(user=self.user)

        data = {
            "old_password": "testpass123",
            "new_password": "newpass123",
            "new_password_confirm": "newpass123",
        }

        response = self.client.post(reverse("accounts:change_password"), data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify password was changed
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("newpass123"))

    def test_websocket_user_info(self):
        """Test WebSocket user info endpoint."""
        self.client.force_authenticate(user=self.user)

        response = self.client.get(reverse("accounts:websocket_user_info"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], self.user.id)
        self.assertEqual(response.data["email"], self.user.email)

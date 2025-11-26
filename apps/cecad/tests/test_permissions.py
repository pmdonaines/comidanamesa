from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User

class CecadImportPermissionTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.import_url = reverse('cecad_import')
        
        # Create a regular user
        self.user = User.objects.create_user(
            username='regular_user',
            password='password123'
        )
        
        # Create a superuser
        self.superuser = User.objects.create_superuser(
            username='super_user',
            password='password123',
            email='admin@example.com'
        )

    def test_regular_user_access_denied(self):
        """Test that a regular user is redirected to dashboard with error message."""
        self.client.login(username='regular_user', password='password123')
        response = self.client.get(self.import_url)
        # Should redirect to dashboard
        self.assertRedirects(response, reverse('cecad_dashboard'))
        
        # Check for error message
        messages = list(response.wsgi_request._messages)
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), "Você não tem permissão para realizar importações.")

    def test_superuser_access_allowed(self):
        """Test that a superuser can access the import page."""
        self.client.login(username='super_user', password='password123')
        response = self.client.get(self.import_url)
        self.assertEqual(response.status_code, 200)

    def test_anonymous_user_redirected(self):
        """Test that an anonymous user is redirected to login."""
        response = self.client.get(self.import_url)
        self.assertNotEqual(response.status_code, 200)
        self.assertNotEqual(response.status_code, 403)
        # Should be redirect to login
        self.assertEqual(response.status_code, 302)

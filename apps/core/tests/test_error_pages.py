from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse

class ErrorTemplatesTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='password')

    def test_404_template(self):
        """Test that the 404 template is used for non-existent URLs."""
        response = self.client.get('/non-existent-url-xyz/')
        self.assertEqual(response.status_code, 404)
        self.assertTemplateUsed(response, '404.html')
        self.assertTemplateUsed(response, 'core/base.html')

    def test_403_template(self):
        """Test that the 403 template is used when accessing restricted page."""
        self.client.login(username='testuser', password='password')
        # Accessing Cecad import page which is restricted to superusers
        url = reverse('cecad_import')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)
        self.assertTemplateUsed(response, '403.html')
        self.assertTemplateUsed(response, 'core/base.html')

"""Regression tests for selected application behavior."""
from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse

from .models import Profile, Ticket


class AccessControlTests(TestCase):
    def setUp(self):
        self.alice = User.objects.create_user('alice', password='password123')
        self.bob = User.objects.create_user('bob', password='password123')
        Profile.objects.create(user=self.alice, role='user')
        Profile.objects.create(user=self.bob, role='user')
        self.private_ticket = Ticket.objects.create(
            owner=self.bob,
            title='Bob private',
            description='secret',
            is_private=True,
        )
        self.client = Client()
        self.client.login(username='alice', password='password123')

    def test_user_cannot_view_foreign_private_ticket(self):
        response = self.client.get(reverse('ticket_detail', args=[self.private_ticket.pk]))
        self.assertIn(response.status_code, [403, 404])

    def test_user_cannot_edit_foreign_ticket(self):
        response = self.client.post(reverse('ticket_edit', args=[self.private_ticket.pk]), {
            'title': 'changed',
            'description': 'changed',
            'priority': 'low',
            'status': 'closed',
            'is_private': 'on',
        })
        self.private_ticket.refresh_from_db()
        self.assertNotEqual(self.private_ticket.title, 'changed')
        self.assertIn(response.status_code, [403, 404])

    def test_user_cannot_self_assign_admin_role(self):
        response = self.client.post(reverse('profile_edit'), {'phone': '123', 'role': 'admin'})
        self.alice.profile.refresh_from_db()
        self.assertEqual(self.alice.profile.role, 'user')


class XssRegressionTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('alice', password='password123')
        Profile.objects.create(user=self.user, role='user')
        self.ticket = Ticket.objects.create(owner=self.user, title='xss', description='demo')
        self.client = Client()
        self.client.login(username='alice', password='password123')

    def test_comment_html_is_escaped(self):
        self.client.post(reverse('comment_add', args=[self.ticket.pk]), {'body': '<script>alert(1)</script>'})
        response = self.client.get(reverse('ticket_detail', args=[self.ticket.pk]))
        self.assertNotContains(response, '<script>alert(1)</script>', html=False)
        self.assertContains(response, '&lt;script&gt;alert(1)&lt;/script&gt;', html=False)

from django.test import TestCase
from django.urls import reverse

from core.models import TournamentRegistration


class PublicRegisterViewTests(TestCase):
	def test_register_page_loads(self):
		response = self.client.get(reverse('public_register'))
		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'Tournament Registration')

	def test_register_submission_creates_record(self):
		response = self.client.post(
			reverse('public_register'),
			{
				'team_name': 'Smash Duo',
				'player1_name': 'Arun',
				'player2_name': 'Kumar',
				'contact_phone': '9999999999',
				'contact_email': 'team@example.com',
				'city': 'Liverpool',
				'notes': 'Weekend availability',
			},
			follow=True,
		)

		self.assertEqual(response.status_code, 200)
		self.assertEqual(TournamentRegistration.objects.count(), 1)
		registration = TournamentRegistration.objects.first()
		self.assertEqual(registration.team_name, 'Smash Duo')

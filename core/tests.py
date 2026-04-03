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
				'player1_first_name': 'Arun',
				'player1_last_name': 'Kumar',
				'player1_category': 'A',
				'player1_contact_number': '9999999999',
				'player1_email': 'arun@example.com',
				'player1_city': 'Liverpool',
				'player2_first_name': 'Ravi',
				'player2_last_name': 'Das',
				'player2_category': 'B',
				'player2_contact_number': '8888888888',
				'player2_email': 'ravi@example.com',
				'player2_city': 'Liverpool',
				'emergency_contact_name': 'Suresh',
				'emergency_contact_number': '7777777777',
				'emergency_contact_relation': 'Brother',
				'declaration_confirmed': 'on',
				'media_consent': 'agree',
			},
			follow=True,
		)

		self.assertEqual(response.status_code, 200)
		self.assertEqual(TournamentRegistration.objects.count(), 1)
		registration = TournamentRegistration.objects.first()
		self.assertEqual(registration.player1_first_name, 'Arun')
		self.assertEqual(registration.player2_first_name, 'Ravi')
		self.assertEqual(registration.emergency_contact_relation, 'Brother')
		self.assertTrue(registration.declaration_confirmed)
		self.assertEqual(registration.media_consent, 'agree')

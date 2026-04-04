from django.test import TestCase
from django.test.utils import override_settings
from django.urls import reverse
from django.core import mail

from core.models import TournamentRegistration


class PublicRegisterViewTests(TestCase):
	def test_register_page_loads(self):
		response = self.client.get(reverse('public_register'))
		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'Tournament Registration')

	@override_settings(
		EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
		REGISTRATION_CONFIRMATION_EMAIL_ASYNC=False,
	)
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
				'declaration_info_true': 'on',
				'declaration_rules_agreed': 'on',
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
		self.assertEqual(len(mail.outbox), 1)
		self.assertIn('NSL Badminton Tournament Registration', mail.outbox[0].subject)

	def test_admin_registered_teams_requires_admin_session(self):
		response = self.client.get(reverse('admin_registered_teams'))
		self.assertEqual(response.status_code, 302)
		self.assertIn('/admin/login', response.url)

	def test_admin_registered_teams_can_edit_registration(self):
		registration = TournamentRegistration.objects.create(
			team_name='Arun Kumar / Ravi Das',
			player1_first_name='Arun',
			player1_last_name='Kumar',
			player1_category='A',
			player1_contact_number='9999999999',
			player1_email='arun@example.com',
			player1_city='Liverpool',
			player2_first_name='Ravi',
			player2_last_name='Das',
			player2_category='B',
			player2_contact_number='8888888888',
			player2_email='ravi@example.com',
			player2_city='Liverpool',
			emergency_contact_name='Suresh',
			emergency_contact_number='7777777777',
			emergency_contact_relation='Brother',
			declaration_confirmed=True,
			media_consent='agree',
		)

		session = self.client.session
		session['is_admin'] = True
		session.save()

		response = self.client.post(
			reverse('admin_registered_teams'),
			{
				'edit_registration': '1',
				'registration_id': registration.id,
				'player1_first_name': 'ArunEdited',
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
				'media_consent': 'do_not_agree',
			},
			follow=True,
		)

		self.assertEqual(response.status_code, 200)
		registration.refresh_from_db()
		self.assertEqual(registration.player1_first_name, 'ArunEdited')
		self.assertEqual(registration.media_consent, 'do_not_agree')

	def test_admin_registered_teams_can_delete_registration(self):
		registration = TournamentRegistration.objects.create(
			team_name='To Delete',
			player1_first_name='A',
			player1_last_name='B',
			player1_category='A',
			player1_contact_number='9999999999',
			player1_email='a@example.com',
			player1_city='Liverpool',
			player2_first_name='C',
			player2_last_name='D',
			player2_category='B',
			player2_contact_number='8888888888',
			player2_email='c@example.com',
			player2_city='Liverpool',
			emergency_contact_name='E',
			emergency_contact_number='7777777777',
			emergency_contact_relation='Brother',
			declaration_confirmed=True,
			media_consent='agree',
		)

		session = self.client.session
		session['is_admin'] = True
		session.save()

		response = self.client.post(
			reverse('admin_registered_teams'),
			{
				'delete_registration': '1',
				'registration_id': registration.id,
			},
			follow=True,
		)

		self.assertEqual(response.status_code, 200)
		self.assertEqual(TournamentRegistration.objects.filter(id=registration.id).count(), 0)

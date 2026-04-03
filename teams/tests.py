from django.test import TestCase
from django.urls import reverse

from core.models import TournamentRegistration
from schedule.models import Round
from teams.models import Team


class AdminTeamsImportFromFormsTests(TestCase):
	def setUp(self):
		session = self.client.session
		session['is_admin'] = True
		session.save()

	def test_import_from_forms_creates_team_rows(self):
		TournamentRegistration.objects.create(
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

		response = self.client.post(reverse('admin_teams'), {'from_forms': '1'}, follow=True)
		self.assertEqual(response.status_code, 200)
		self.assertEqual(Team.objects.count(), 1)
		team = Team.objects.first()
		self.assertEqual(team.player1_name, 'Arun Kumar')
		self.assertEqual(team.player2_name, 'Ravi Das')

	def test_unlock_teams_resets_round_locks_and_court_lock(self):
		Round.objects.create(
			name='Group Stage',
			order=1,
			is_finished=True,
			settings_locked=True,
			points_per_set=30,
			sets_per_match=3,
		)
		Team.objects.create(
			player1_name='P1',
			player2_name='P2',
			team_name='P1 & P2',
			is_locked=True,
		)

		session = self.client.session
		session['locked_num_courts'] = 4
		session.save()

		response = self.client.post(
			reverse('admin_teams'),
			{
				'unlock_teams': '1',
				'admin_password': 'admin123',
			},
			follow=True,
		)

		self.assertEqual(response.status_code, 200)
		round_obj = Round.objects.get(order=1)
		self.assertFalse(round_obj.is_finished)
		self.assertFalse(round_obj.settings_locked)
		self.assertEqual(round_obj.points_per_set, 21)
		self.assertEqual(round_obj.sets_per_match, 1)
		self.assertIsNone(self.client.session.get('locked_num_courts'))

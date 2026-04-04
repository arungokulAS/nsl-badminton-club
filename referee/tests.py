from django.test import TestCase
from django.urls import reverse

from matches.models import Match
from results.models import Score
from schedule.models import Court, Round
from teams.models import Team


class AdminLiveManageTests(TestCase):
	def setUp(self):
		session = self.client.session
		session['is_admin'] = True
		session.save()

		self.round = Round.objects.create(name='Group Stage', order=1, sets_per_match=2)
		self.court = Court.objects.create(name='Court 1')
		self.team1 = Team.objects.create(player1_name='A1', player2_name='A2', team_name='Team A', is_locked=True)
		self.team2 = Team.objects.create(player1_name='B1', player2_name='B2', team_name='Team B', is_locked=True)
		self.match = Match.objects.create(
			round=self.round,
			team1=self.team1,
			team2=self.team2,
			court=self.court,
			status='awaiting_admin_confirmation',
		)
		self.score = Score.objects.create(
			match=self.match,
			team1_score=42,
			team2_score=36,
			team1_set1=21,
			team2_set1=18,
			team1_set2=21,
			team2_set2=18,
			set1_submitted=True,
			set2_submitted=True,
			locked=False,
		)

	def test_admin_live_manage_does_not_show_winner_selection(self):
		response = self.client.get(reverse('admin_live_manage'))
		self.assertEqual(response.status_code, 200)
		self.assertNotContains(response, 'Select Winner')
		self.assertContains(response, 'Pending')
		self.assertContains(response, 'Save')

	def test_admin_live_manage_shows_dash_before_referee_submission(self):
		new_match = Match.objects.create(
			round=self.round,
			team1=self.team1,
			team2=self.team2,
			court=self.court,
			status='scheduled',
		)
		response = self.client.get(reverse('admin_live_manage'))
		self.assertEqual(response.status_code, 200)
		self.assertContains(response, '<span style="color:#d8d8d8;">-</span>', html=True)

	def test_admin_live_manage_save_and_edit_cycle(self):
		response = self.client.post(
			reverse('admin_live_manage'),
			{
				'match_id': self.match.id,
				'action': 'save_score',
				'team1_value': '40',
				'team2_value': '35',
			},
			follow=True,
		)

		self.assertEqual(response.status_code, 200)
		self.match.refresh_from_db()
		self.score.refresh_from_db()
		self.assertEqual(self.match.status, 'completed')
		self.assertTrue(self.score.locked)
		self.assertEqual(self.score.winner_id, self.team1.id)
		self.assertEqual(self.score.team1_score, 40)
		self.assertEqual(self.score.team2_score, 35)
		self.assertContains(response, 'Confirmed')
		self.assertContains(response, 'Edit')

		edit_response = self.client.post(
			reverse('admin_live_manage'),
			{
				'match_id': self.match.id,
				'action': 'edit_score',
			},
			follow=True,
		)

		self.assertEqual(edit_response.status_code, 200)
		self.match.refresh_from_db()
		self.score.refresh_from_db()
		self.assertEqual(self.match.status, 'awaiting_admin_confirmation')
		self.assertFalse(self.score.locked)
		self.assertContains(edit_response, 'Pending')
		self.assertContains(edit_response, 'Save')

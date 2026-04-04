from django.test import TestCase
from django.urls import reverse
import os

from groups.models import Group
from matches.models import Match
from schedule.models import Court, Round
from teams.models import Team


class AdminGroupsViewTests(TestCase):
	def setUp(self):
		session = self.client.session
		session['is_admin'] = True
		session['locked_num_courts'] = 4
		session.save()

		self.team1 = Team.objects.create(
			player1_name='Player 1A',
			player2_name='Player 1B',
			team_name='Team 1',
			is_locked=True,
		)
		self.team2 = Team.objects.create(
			player1_name='Player 2A',
			player2_name='Player 2B',
			team_name='Team 2',
			is_locked=True,
		)

		self.group = Group.objects.create(group_name='A', is_locked=False)
		self.group.teams.set([self.team1, self.team2])

		self.group_stage = Round.objects.create(
			name='Group Stage',
			order=1,
			is_finished=True,
			settings_locked=True,
			points_per_set=15,
			sets_per_match=3,
		)
		self.final_round = Round.objects.create(
			name='Final',
			order=7,
			is_finished=True,
			settings_locked=True,
			points_per_set=15,
			sets_per_match=3,
		)
		court = Court.objects.create(name='Court 1')
		Match.objects.create(
			round=self.group_stage,
			group=self.group,
			team1=self.team1,
			team2=self.team2,
			court=court,
			status='completed',
		)

	def test_lock_groups_resets_schedule_state(self):
		admin_password = os.environ.get('ADMIN_PASSWORD', 'admin123')
		response = self.client.post(
			reverse('admin_groups'),
			{'lock_groups': '1', 'admin_password': admin_password},
			follow=True,
		)

		self.assertEqual(response.status_code, 200)
		self.group.refresh_from_db()
		self.assertTrue(self.group.is_locked)
		self.assertEqual(Match.objects.count(), 0)

		self.group_stage.refresh_from_db()
		self.final_round.refresh_from_db()
		self.assertFalse(self.group_stage.is_finished)
		self.assertFalse(self.final_round.is_finished)
		self.assertFalse(self.group_stage.settings_locked)
		self.assertFalse(self.final_round.settings_locked)
		self.assertEqual(self.group_stage.points_per_set, 21)
		self.assertEqual(self.group_stage.sets_per_match, 1)
		self.assertEqual(self.final_round.points_per_set, 21)
		self.assertEqual(self.final_round.sets_per_match, 1)
		self.assertIsNone(self.client.session.get('locked_num_courts'))

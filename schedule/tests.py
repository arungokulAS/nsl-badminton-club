
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
import os
from schedule.models import Round, Court
from teams.models import Team
from groups.models import Group
from matches.models import Match
from results.models import Score
from live.utils import build_qualifier_table

class AdminScheduleViewTests(TestCase):
	def setUp(self):
		self.client = Client()
		# Simulate admin session
		session = self.client.session
		session['is_admin'] = True
		session.save()
		# Create courts
		self.court1 = Court.objects.create(name='Court 1')
		self.court2 = Court.objects.create(name='Court 2')
		self.court3 = Court.objects.create(name='Court 3')
		self.court4 = Court.objects.create(name='Court 4')
		# Create rounds
		self.round1 = Round.objects.create(name='Group Stage', order=1)
		self.round2 = Round.objects.create(name='Qualifier', order=2)
		# Create 6 groups with 6 teams each
		group_codes = ['A', 'B', 'C', 'D', 'E', 'F']
		team_index = 1
		for code in group_codes:
			group = Group.objects.create(group_name=f'Group {code}', is_locked=True)
			teams = []
			for _ in range(6):
				teams.append(
					Team.objects.create(
						player1_name=f'P{team_index}A',
						player2_name=f'P{team_index}B',
						team_name=f'Team {team_index}',
						is_locked=True,
					)
				)
				team_index += 1
			group.teams.set(teams)

	def test_admin_schedule_get(self):
		response = self.client.get(reverse('admin_schedule'))
		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'Admin Schedule Management')

	def test_admin_schedule_generate_group_stage(self):
		response = self.client.post(reverse('admin_schedule'), {
			'generate_schedule': '1',
			'round': self.round1.id,
			'num_courts': 4
		}, follow=True)
		self.assertRedirects(response, reverse('admin_schedule'))
		matches = Match.objects.filter(round=self.round1)
		self.assertEqual(matches.count(), 90)
		# Each match should have two teams and a court
		for match in matches:
			self.assertIsNotNone(match.team1)
			self.assertIsNotNone(match.team2)
			self.assertIsNotNone(match.court)

	def test_admin_schedule_enforce_round_order(self):
		# Try to generate schedule for round2 before round1 is finished
		response = self.client.post(reverse('admin_schedule'), {
			'generate_schedule': '1',
			'round': self.round2.id,
			'num_courts': 4
		}, follow=True)
		self.assertEqual(response.status_code, 200)
		self.assertEqual(Match.objects.filter(round=self.round2).count(), 0)

	def test_admin_schedule_prevent_duplicate_schedule(self):
		# Generate once
		self.client.post(reverse('admin_schedule'), {
			'generate_schedule': '1',
			'round': self.round1.id,
			'num_courts': 4
		}, follow=True)
		# Try to generate again for same round
		response = self.client.post(reverse('admin_schedule'), {
			'generate_schedule': '1',
			'round': self.round1.id,
			'num_courts': 4
		}, follow=True)
		self.assertEqual(response.status_code, 200)
		self.assertEqual(Match.objects.filter(round=self.round1).count(), 90)

	def test_admin_schedule_no_same_team_in_same_slot_across_courts(self):
		self.client.post(reverse('admin_schedule'), {
			'generate_schedule': '1',
			'round': self.round1.id,
			'num_courts': 4
		}, follow=True)

		matches_by_court = {
			court.id: list(Match.objects.filter(round=self.round1, court=court).order_by('id'))
			for court in Court.objects.order_by('id')
		}
		max_slots = max((len(matches) for matches in matches_by_court.values()), default=0)

		for slot in range(max_slots):
			teams_in_slot = set()
			for court_matches in matches_by_court.values():
				if slot >= len(court_matches):
					continue
				match = court_matches[slot]
				for team_id in (match.team1_id, match.team2_id):
					self.assertNotIn(team_id, teams_in_slot)
					teams_in_slot.add(team_id)

	def test_unlock_round_settings_works_for_multiple_rounds(self):
		team1 = Team.objects.order_by('id').first()
		team2 = Team.objects.order_by('id')[1]
		final_round = Round.objects.create(name='Final', order=7)

		Match.objects.create(round=self.round1, team1=team1, team2=team2, court=self.court1, status='scheduled')
		Match.objects.create(round=final_round, team1=team1, team2=team2, court=self.court2, status='scheduled')

		self.round1.settings_locked = True
		self.round1.save(update_fields=['settings_locked'])
		final_round.settings_locked = True
		final_round.save(update_fields=['settings_locked'])

		admin_password = os.environ.get('ADMIN_PASSWORD', 'admin123')

		for target_round in (self.round1, final_round):
			response = self.client.post(
				reverse('admin_schedule'),
				{
					'unlock_round_settings': '1',
					'round_id': target_round.id,
					'admin_password': admin_password,
				},
			)
			self.assertEqual(response.status_code, 302)
			self.assertEqual(response.url, f'/admin/schedule?show_round={target_round.id}')

			updated_round = Round.objects.get(id=target_round.id)
			self.assertFalse(updated_round.settings_locked)

	def test_prequarter_schedule_pairs_seed_1_vs_16(self):
		self.round1.is_finished = True
		self.round1.save(update_fields=['is_finished'])
		self.round2.is_finished = True
		self.round2.save(update_fields=['is_finished'])
		prequarter_round = Round.objects.create(name='Pre-Quarter', order=3)

		teams = list(Team.objects.order_by('id')[:16])
		for idx in range(0, 16, 2):
			team1 = teams[idx]
			team2 = teams[idx + 1]
			match = Match.objects.create(
				round=self.round2,
				team1=team1,
				team2=team2,
				court=self.court1,
				status='completed',
			)
			Score.objects.create(
				match=match,
				team1_score=21,
				team2_score=10 + (idx // 2),
				winner=team1,
				locked=True,
			)

		response = self.client.post(
			reverse('admin_schedule'),
			{
				'generate_schedule': '1',
				'round': prequarter_round.id,
				'num_courts': 4,
			},
			follow=True,
		)

		self.assertEqual(response.status_code, 200)
		prequarter_matches = list(Match.objects.filter(round=prequarter_round).order_by('id'))
		self.assertEqual(len(prequarter_matches), 8)

		seeded_teams = [row['team'] for row in build_qualifier_table(self.round2)[:16]]
		expected_pairings = [(seeded_teams[i], seeded_teams[-(i + 1)]) for i in range(8)]
		actual_pairings = [(match.team1, match.team2) for match in prequarter_matches]
		self.assertEqual(actual_pairings, expected_pairings)

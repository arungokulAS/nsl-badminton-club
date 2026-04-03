
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from schedule.models import Round, Court
from teams.models import Team
from groups.models import Group
from matches.models import Match

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

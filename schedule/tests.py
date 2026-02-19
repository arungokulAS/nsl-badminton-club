
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
		# Create rounds
		self.round1 = Round.objects.create(name='Group Stage', order=1)
		self.round2 = Round.objects.create(name='Quarterfinal', order=2)
		# Create teams
		self.team1 = Team.objects.create(player1_name='A', player2_name='B', team_name='A & B', is_locked=True)
		self.team2 = Team.objects.create(player1_name='C', player2_name='D', team_name='C & D', is_locked=True)
		self.team3 = Team.objects.create(player1_name='E', player2_name='F', team_name='E & F', is_locked=True)
		self.team4 = Team.objects.create(player1_name='G', player2_name='H', team_name='G & H', is_locked=True)
		# Create group
		self.group = Group.objects.create(group_name='A', is_locked=True)
		self.group.teams.set([self.team1, self.team2, self.team3, self.team4])

	def test_admin_schedule_get(self):
		response = self.client.get(reverse('admin_schedule'))
		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'Admin Schedule Management')

	def test_admin_schedule_generate_group_stage(self):
		response = self.client.post(reverse('admin_schedule'), {
			'generate_schedule': '1',
			'round': self.round1.id,
			'num_courts': 2
		}, follow=True)
		self.assertRedirects(response, reverse('admin_schedule'))
		matches = Match.objects.filter(round=self.round1)
		self.assertEqual(matches.count(), 2)
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
			'num_courts': 2
		}, follow=True)
		self.assertContains(response, 'You can only schedule the next unfinished round.')

	def test_admin_schedule_prevent_duplicate_schedule(self):
		# Generate once
		self.client.post(reverse('admin_schedule'), {
			'generate_schedule': '1',
			'round': self.round1.id,
			'num_courts': 2
		}, follow=True)
		# Try to generate again for same round
		response = self.client.post(reverse('admin_schedule'), {
			'generate_schedule': '1',
			'round': self.round1.id,
			'num_courts': 2
		}, follow=True)
		self.assertContains(response, 'Schedule for this round already exists.')

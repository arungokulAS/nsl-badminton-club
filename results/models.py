from django.db import models
from matches.models import Match
from teams.models import Team

class Score(models.Model):
	match = models.OneToOneField(Match, on_delete=models.CASCADE)
	team1_score = models.PositiveIntegerField()
	team2_score = models.PositiveIntegerField()
	team1_set1 = models.PositiveIntegerField(null=True, blank=True)
	team2_set1 = models.PositiveIntegerField(null=True, blank=True)
	team1_set2 = models.PositiveIntegerField(null=True, blank=True)
	team2_set2 = models.PositiveIntegerField(null=True, blank=True)
	team1_set3 = models.PositiveIntegerField(null=True, blank=True)
	team2_set3 = models.PositiveIntegerField(null=True, blank=True)
	set1_submitted = models.BooleanField(default=False)
	set2_submitted = models.BooleanField(default=False)
	set3_submitted = models.BooleanField(default=False)
	winner = models.ForeignKey(Team, related_name='won_matches', on_delete=models.SET_NULL, null=True)
	locked = models.BooleanField(default=False)

	def __str__(self):
		return f"{self.match}: {self.team1_score}-{self.team2_score}"

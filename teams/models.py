from django.db import models

class Team(models.Model):
	player1_name = models.CharField(max_length=100)
	player2_name = models.CharField(max_length=100)
	team_name = models.CharField(max_length=200, unique=True)
	is_locked = models.BooleanField(default=False)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	def __str__(self):
		return self.team_name

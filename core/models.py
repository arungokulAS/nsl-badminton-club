from django.db import models


class TournamentRegistration(models.Model):
	team_name = models.CharField(max_length=200)
	player1_name = models.CharField(max_length=100)
	player2_name = models.CharField(max_length=100)
	contact_phone = models.CharField(max_length=20)
	contact_email = models.EmailField(blank=True)
	city = models.CharField(max_length=100, blank=True)
	notes = models.TextField(blank=True)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ["-created_at"]

	def __str__(self):
		return self.team_name

from django.db import models


class TournamentRegistration(models.Model):
	team_name = models.CharField(max_length=200, blank=True)
	player1_first_name = models.CharField(max_length=100)
	player1_last_name = models.CharField(max_length=100)
	player1_category = models.CharField(max_length=1)
	player1_contact_number = models.CharField(max_length=20)
	player1_email = models.EmailField()
	player1_city = models.CharField(max_length=100)
	player2_first_name = models.CharField(max_length=100)
	player2_last_name = models.CharField(max_length=100)
	player2_category = models.CharField(max_length=1)
	player2_contact_number = models.CharField(max_length=20)
	player2_email = models.EmailField()
	player2_city = models.CharField(max_length=100)
	emergency_contact_name = models.CharField(max_length=100)
	emergency_contact_number = models.CharField(max_length=20)
	emergency_contact_relation = models.CharField(max_length=20)
	declaration_confirmed = models.BooleanField(default=False)
	media_consent = models.CharField(max_length=20, default='do_not_agree')
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ["-created_at"]

	def __str__(self):
		if self.team_name:
			return self.team_name
		return f"{self.player1_first_name} & {self.player2_first_name}"

from django.db import models
from teams.models import Team

class Group(models.Model):
	group_name = models.CharField(max_length=20)
	teams = models.ManyToManyField(Team, related_name='groups')
	is_locked = models.BooleanField(default=False)

	def __str__(self):
		return self.group_name

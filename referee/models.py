from django.db import models
from schedule.models import Court

class Referee(models.Model):
	name = models.CharField(max_length=100)
	assigned_courts = models.ManyToManyField(Court, related_name='referees')

	def __str__(self):
		return self.name

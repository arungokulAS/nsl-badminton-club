from django.db import models

class Court(models.Model):
	name = models.CharField(max_length=20)

	def __str__(self):
		return self.name

class Round(models.Model):
	name = models.CharField(max_length=30)  # e.g., group, qualifier, pre-quarter, etc.
	order = models.PositiveIntegerField()
	is_finished = models.BooleanField(default=False)
	points_per_set = models.PositiveIntegerField(default=21)
	sets_per_match = models.PositiveIntegerField(default=1)
	settings_locked = models.BooleanField(default=False)

	def __str__(self):
		return self.name

from django.db import models

class Court(models.Model):
	name = models.CharField(max_length=20)

	def __str__(self):
		return self.name

class Round(models.Model):
	name = models.CharField(max_length=30)  # e.g., group, qualifier, pre-quarter, etc.
	order = models.PositiveIntegerField()
	is_finished = models.BooleanField(default=False)

	def __str__(self):
		return self.name

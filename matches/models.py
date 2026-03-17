from django.db import models
from teams.models import Team
from schedule.models import Round, Court


from groups.models import Group

class Match(models.Model):
	round = models.ForeignKey(Round, on_delete=models.CASCADE)
	group = models.ForeignKey(Group, on_delete=models.SET_NULL, null=True, blank=True)
	team1 = models.ForeignKey(Team, related_name='team1_matches', on_delete=models.CASCADE)
	team2 = models.ForeignKey(Team, related_name='team2_matches', on_delete=models.CASCADE)
	court = models.ForeignKey(Court, on_delete=models.SET_NULL, null=True)
	status = models.CharField(max_length=50, default='scheduled')  # scheduled, completed, locked, etc.

	def __str__(self):
		group_str = f" [{self.group.group_name}]" if self.group else ""
		return f"{self.team1} vs {self.team2} ({self.round}){group_str}"

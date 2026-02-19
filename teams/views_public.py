from django.shortcuts import render
from teams.models import Team

def public_teams(request):
    teams = Team.objects.all().order_by('team_name')
    context = {
        'teams': teams,
    }
    return render(request, 'teams/public_teams.html', context)

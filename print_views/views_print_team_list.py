from django.shortcuts import render
from teams.models import Team
from groups.models import Group

def print_team_list(request):
    # Get all teams with their groups
    teams = Team.objects.all().order_by('team_name')
    # Build a mapping of team to group (assume one group per team for print)
    team_group_map = {}
    for group in Group.objects.all():
        for team in group.teams.all():
            team_group_map[team.id] = group
    # Attach group to each team for template
    for team in teams:
        team.group = team_group_map.get(team.id)
    context = {
        'teams': teams,
    }
    return render(request, 'print_views/print_team_list.html', context)

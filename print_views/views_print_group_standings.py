from django.shortcuts import render
from groups.models import Group
from results.models import Score
from matches.models import Match

def print_group_standings(request):
    groups = Group.objects.prefetch_related('teams').all().order_by('group_name')
    # Calculate standings: wins, losses, points for each team
    standings = {}
    for group in groups:
        for team in group.teams.all():
            standings[team.id] = {'wins': 0, 'losses': 0, 'points': 0}
    for score in Score.objects.select_related('match', 'winner').all():
        t1 = score.match.team1
        t2 = score.match.team2
        if t1.id in standings and t2.id in standings:
            if score.winner_id == t1.id:
                standings[t1.id]['wins'] += 1
                standings[t1.id]['points'] += 2
                standings[t2.id]['losses'] += 1
            elif score.winner_id == t2.id:
                standings[t2.id]['wins'] += 1
                standings[t2.id]['points'] += 2
                standings[t1.id]['losses'] += 1
    context = {
        'groups': groups,
        'standings': standings,
    }
    return render(request, 'print_views/print_group_standings.html', context)

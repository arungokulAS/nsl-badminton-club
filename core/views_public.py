from django.shortcuts import render

from groups.models import Group
from matches.models import Match
from schedule.models import Round
from teams.models import Team

STANDARD_ROUND_NAMES = [
    'Group Stage',
    'Qualifier',
    'Pre-Quarter',
    'Quarter',
    'Semi Final',
    'Losers Final',
    'Final',
]

def public_referee(request):
    return render(request, 'core/public_referee.html')

def public_contact(request):
    return render(request, 'core/public_contact.html')

def print_menu(request):
    teams = Team.objects.all().order_by('team_name')
    groups = Group.objects.prefetch_related('teams').all().order_by('group_name')
    rounds = Round.objects.filter(order__in=[1, 2, 3, 4, 5, 6, 7], name__in=STANDARD_ROUND_NAMES).order_by('order')
    matches = Match.objects.select_related('round', 'court', 'team1', 'team2').filter(
        round__order__in=[1, 2, 3, 4, 5, 6, 7],
        round__name__in=STANDARD_ROUND_NAMES,
    ).order_by('round__order', 'court__name', 'id')
    context = {
        'teams': teams,
        'groups': groups,
        'rounds': rounds,
        'matches': matches,
    }
    return render(request, 'core/print_menu.html', context)

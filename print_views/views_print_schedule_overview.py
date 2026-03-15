from django.shortcuts import render
from matches.models import Match
from schedule.models import Round

STANDARD_ROUND_NAMES = [
    'Group Stage',
    'Qualifier',
    'Pre-Quarter',
    'Quarter',
    'Semi Final',
    'Losers Final',
    'Final',
]

def print_schedule_overview(request):
    rounds = Round.objects.filter(order__in=[1, 2, 3, 4, 5, 6, 7], name__in=STANDARD_ROUND_NAMES).order_by('order')
    round_tables = []
    for round_obj in rounds:
        round_matches = Match.objects.select_related('team1', 'team2', 'court', 'round', 'group').filter(
            round=round_obj
        ).order_by('court__id', 'id')
        round_tables.append({
            'round': round_obj,
            'matches': list(round_matches),
        })
    context = {
        'round_tables': round_tables,
    }
    return render(request, 'print_views/print_schedule_overview.html', context)

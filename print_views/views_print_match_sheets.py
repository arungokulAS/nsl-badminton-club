from django.shortcuts import render
from matches.models import Match

STANDARD_ROUND_NAMES = [
    'Group Stage',
    'Qualifier',
    'Pre-Quarter',
    'Quarter',
    'Semi Final',
    'Losers Final',
    'Final',
]

def print_match_sheets(request):
    matches = Match.objects.select_related('team1', 'team2', 'court', 'round').filter(round__order__in=[1, 2, 3, 4, 5, 6, 7], round__name__in=STANDARD_ROUND_NAMES).order_by('round__order', 'court__id')
    context = {
        'matches': matches,
    }
    return render(request, 'print_views/print_match_sheets.html', context)

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
    sheets = [
        {'points': 15, 'rows': range(1, 16)},
        {'points': 21, 'rows': range(1, 22)},
        {'points': 30, 'rows': range(1, 31)},
    ]
    context = {
        'matches': matches,
        'sheets': sheets,
    }
    return render(request, 'print_views/print_match_sheets.html', context)

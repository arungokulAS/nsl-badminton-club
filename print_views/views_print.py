from django.shortcuts import render
from matches.models import Match
from results.models import Score
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

def print_bracket(request):
    rounds = Round.objects.filter(order__in=[1, 2, 3, 4, 5, 6, 7], name__in=STANDARD_ROUND_NAMES).order_by('order')
    matches = Match.objects.select_related('team1', 'team2', 'court', 'round').filter(round__order__in=[1, 2, 3, 4, 5, 6, 7], round__name__in=STANDARD_ROUND_NAMES).order_by('round__order', 'court__id')
    scores = {s.match_id: s for s in Score.objects.filter(match__round__order__in=[1, 2, 3, 4, 5, 6, 7], match__round__name__in=STANDARD_ROUND_NAMES)}
    context = {
        'rounds': rounds,
        'matches': matches,
        'scores': scores,
    }
    return render(request, 'print_views/print_bracket.html', context)

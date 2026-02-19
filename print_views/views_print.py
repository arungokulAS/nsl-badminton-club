from django.shortcuts import render
from matches.models import Match
from results.models import Score
from schedule.models import Round

def print_bracket(request):
    rounds = Round.objects.all().order_by('order')
    matches = Match.objects.select_related('team1', 'team2', 'court', 'round').all().order_by('round__order', 'court__id')
    scores = {s.match_id: s for s in Score.objects.all()}
    context = {
        'rounds': rounds,
        'matches': matches,
        'scores': scores,
    }
    return render(request, 'print_views/print_bracket.html', context)

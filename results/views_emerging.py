from django.shortcuts import render

from matches.models import Match
from results.models import Score
from schedule.models import Round


EMERGING_ROUNDS = ['Emerging Quarter', 'Emerging Semi Final', 'Emerging Final']


def public_emerging_results(request):
    rounds = Round.objects.filter(name__in=EMERGING_ROUNDS).order_by('order', 'id')
    matches = Match.objects.filter(round__in=rounds).select_related('team1', 'team2', 'round').order_by('round__order', 'id')
    scores = {score.match_id: score for score in Score.objects.filter(match__in=matches, locked=True)}

    final_round = rounds.filter(name='Emerging Final').first()
    champion = None
    if final_round:
        final_match = matches.filter(round=final_round).first()
        final_score = scores.get(final_match.id) if final_match else None
        if final_score and final_score.winner:
            champion = final_score.winner

    context = {
        'rounds': rounds,
        'matches': matches,
        'scores': scores,
        'champion': champion,
    }
    return render(request, 'results/public_emerging_results.html', context)

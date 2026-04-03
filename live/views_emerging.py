from django.shortcuts import render

from matches.models import Match
from results.models import Score
from schedule.models import Round


EMERGING_ROUNDS = ['Emerging Quarter', 'Emerging Semi Final', 'Emerging Final']


def public_emerging_live(request):
    rounds = Round.objects.filter(name__in=EMERGING_ROUNDS).order_by('order', 'id')
    selected_round = rounds.filter(is_finished=False).first() if rounds.exists() else None

    round_id = request.GET.get('round_id')
    if round_id:
        try:
            selected_round = rounds.get(id=int(round_id))
        except Exception:
            pass

    matches = Match.objects.none()
    if selected_round:
        matches = Match.objects.filter(round=selected_round).select_related('team1', 'team2', 'court', 'round')

    context = {
        'rounds': rounds,
        'selected_round': selected_round,
        'matches': matches,
        'scores': {score.match_id: score for score in Score.objects.filter(match__in=matches, locked=True)},
    }
    return render(request, 'live/public_emerging_live.html', context)

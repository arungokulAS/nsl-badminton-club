from django.shortcuts import render
from matches.models import Match
from schedule.models import Round, Court

STANDARD_ROUND_NAMES = [
    'Group Stage',
    'Qualifier',
    'Pre-Quarter',
    'Quarter',
    'Semi Final',
    'Losers Final',
    'Final',
]

def public_schedule(request):
    rounds = Round.objects.filter(order__in=[1, 2, 3, 4, 5, 6, 7], name__in=STANDARD_ROUND_NAMES).order_by('order')
    current_round = rounds.filter(is_finished=False).order_by('order').first()
    locked_num_courts = request.session.get('locked_num_courts')
    courts = Court.objects.all().order_by('id')
    if locked_num_courts:
        courts = courts[: int(locked_num_courts)]
    matches = Match.objects.select_related('team1', 'team2', 'court', 'round', 'group').filter(
        round__order__in=[1, 2, 3, 4, 5, 6, 7],
        round__name__in=STANDARD_ROUND_NAMES,
    ).order_by('round__order', 'court__id', 'id')
    court_match_groups = []
    if current_round:
        for court in courts:
            court_matches = matches.filter(round=current_round, court=court).order_by('id')
            if court_matches.exists():
                court_match_groups.append({
                    'court': court,
                    'matches': list(court_matches),
                })
    context = {
        'rounds': rounds,
        'current_round': current_round,
        'courts': courts,
        'matches': matches,
        'court_match_groups': court_match_groups,
    }
    return render(request, 'schedule/public_schedule.html', context)

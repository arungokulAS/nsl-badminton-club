from django.http import JsonResponse
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

def public_schedule_api(request):
    rounds = list(Round.objects.filter(order__in=[1, 2, 3, 4, 5, 6, 7], name__in=STANDARD_ROUND_NAMES).order_by('order').values('id', 'name', 'order'))
    courts = list(Court.objects.all().order_by('id').values('id', 'name'))
    matches = list(Match.objects.select_related('team1', 'team2', 'court', 'round').filter(round__order__in=[1, 2, 3, 4, 5, 6, 7], round__name__in=STANDARD_ROUND_NAMES).order_by('round__order', 'court__id').values('id', 'team1__team_name', 'team2__team_name', 'court__id', 'court__name', 'round__id', 'round__name', 'status'))
    return JsonResponse({'rounds': rounds, 'courts': courts, 'matches': matches})

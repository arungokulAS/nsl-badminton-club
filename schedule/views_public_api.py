from django.http import JsonResponse
from matches.models import Match
from schedule.models import Round, Court

def public_schedule_api(request):
    rounds = list(Round.objects.all().order_by('order').values('id', 'name', 'order'))
    courts = list(Court.objects.all().order_by('id').values('id', 'name'))
    matches = list(Match.objects.select_related('team1', 'team2', 'court', 'round').all().order_by('round__order', 'court__id').values('id', 'team1__team_name', 'team2__team_name', 'court__id', 'court__name', 'round__id', 'round__name', 'status'))
    return JsonResponse({'rounds': rounds, 'courts': courts, 'matches': matches})

from django.http import JsonResponse
from matches.models import Match
from schedule.models import Round

def public_live_api(request):
    # Show only matches that are ongoing or about to start
    live_matches = list(Match.objects.select_related('team1', 'team2', 'court', 'round')
        .filter(status__in=['scheduled', 'in_progress'])
        .order_by('round__order', 'court__id')
        .values('id', 'team1__team_name', 'team2__team_name', 'court__id', 'court__name', 'round__id', 'round__name', 'status'))
    return JsonResponse({'live_matches': live_matches})

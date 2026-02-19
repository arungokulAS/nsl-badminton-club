from django.http import JsonResponse
from teams.models import Team

def public_teams_api(request):
    teams = list(Team.objects.all().order_by('team_name').values('id', 'team_name'))
    return JsonResponse({'teams': teams})

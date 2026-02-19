from django.http import JsonResponse
from groups.models import Group
from teams.models import Team

def public_groups_api(request):
    groups = []
    for group in Group.objects.all().order_by('group_name'):
        teams = list(group.teams.all().order_by('team_name').values('id', 'team_name'))
        groups.append({'id': group.id, 'name': group.group_name, 'teams': teams})
    return JsonResponse({'groups': groups})

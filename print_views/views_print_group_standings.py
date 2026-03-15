from django.shortcuts import render
from groups.models import Group

def print_group_standings(request):
    groups = Group.objects.all().order_by('group_name')
    context = {
        'groups': groups,
    }
    return render(request, 'print_views/print_group_standings.html', context)

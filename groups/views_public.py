from django.shortcuts import render
from groups.models import Group

def public_groups(request):
    groups = Group.objects.all().order_by('group_name')
    context = {'groups': groups}
    return render(request, 'groups/public_groups.html', context)

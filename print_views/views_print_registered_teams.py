from django.shortcuts import render

from core.models import TournamentRegistration


def print_registered_teams(request):
    registrations = TournamentRegistration.objects.all().order_by('created_at', 'id')
    context = {
        'registrations': registrations,
    }
    return render(request, 'print_views/print_registered_teams.html', context)

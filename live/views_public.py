from django.shortcuts import render
from matches.models import Match
from schedule.models import Round

def public_live(request):
    matches = Match.objects.filter(status__in=['scheduled', 'in_progress']).select_related('team1', 'team2', 'court', 'round').order_by('round__order', 'court__id')
    context = {'matches': matches}
    return render(request, 'live/public_live.html', context)

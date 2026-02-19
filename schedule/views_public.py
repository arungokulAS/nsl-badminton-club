from django.shortcuts import render
from matches.models import Match
from schedule.models import Round, Court

def public_schedule(request):
    rounds = Round.objects.all().order_by('order')
    courts = Court.objects.all().order_by('id')
    matches = Match.objects.select_related('team1', 'team2', 'court', 'round').all().order_by('round__order', 'court__id')
    context = {
        'rounds': rounds,
        'courts': courts,
        'matches': matches,
    }
    return render(request, 'schedule/public_schedule.html', context)

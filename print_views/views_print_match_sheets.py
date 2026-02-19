from django.shortcuts import render
from matches.models import Match

def print_match_sheets(request):
    matches = Match.objects.select_related('team1', 'team2', 'court', 'round').all().order_by('round__order', 'court__id')
    context = {
        'matches': matches,
    }
    return render(request, 'print_views/print_match_sheets.html', context)

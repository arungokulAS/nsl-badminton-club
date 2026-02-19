from django.http import JsonResponse
from matches.models import Match
from results.models import Score
from schedule.models import Round

def public_results_api(request):
    rounds = list(Round.objects.all().order_by('order').values('id', 'name', 'order'))
    matches = list(Match.objects.select_related('team1', 'team2', 'court', 'round').all().order_by('round__order', 'court__id').values('id', 'team1__team_name', 'team2__team_name', 'court__id', 'court__name', 'round__id', 'round__name', 'status'))
    scores = {s.match_id: {'score1': s.score1, 'score2': s.score2} for s in Score.objects.all()}
    return JsonResponse({'rounds': rounds, 'matches': matches, 'scores': scores})

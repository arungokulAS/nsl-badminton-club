from django.shortcuts import render
from matches.models import Match

def print_match_sheets(request):
    score_options = [15, 21, 30]
    selected_points_raw = request.GET.get('points', '').strip()
    selected_points = int(selected_points_raw) if selected_points_raw in {'15', '21', '30'} else None

    matches_queryset = Match.objects.select_related('team1', 'team2', 'court', 'round', 'group').filter(
        round__name='Group Stage'
    ).order_by('court__id', 'id')

    sheets = []
    if selected_points:
        for match_index, match in enumerate(matches_queryset, start=1):
            sheets.append(
                {
                    'points': selected_points,
                    'rows': range(1, selected_points + 1),
                    'match_no': match_index,
                    'group_name': match.group.group_name if match.group else '-',
                    'team1_name': match.team1.team_name if match.team1 else '-',
                    'team2_name': match.team2.team_name if match.team2 else '-',
                }
            )

    context = {
        'score_options': score_options,
        'selected_points': selected_points,
        'sheets': sheets,
    }
    return render(request, 'print_views/print_match_sheets.html', context)

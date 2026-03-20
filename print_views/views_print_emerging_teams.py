from django.shortcuts import render

from live.utils import build_group_tables


def print_emerging_teams(request):
    group_tables = build_group_tables()
    emerging_rows = []
    for group_table in group_tables:
        for row in group_table['rows']:
            if row.get('is_eliminated'):
                emerging_rows.append({
                    'team': row['team'],
                    'points_diff': row['diff'],
                })
    emerging_rows.sort(key=lambda row: (row['points_diff'], row['team'].team_name))
    context = {
        'emerging_rows': emerging_rows,
    }
    return render(request, 'print_views/print_emerging_teams.html', context)

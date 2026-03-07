from django.shortcuts import render
from matches.models import Match
from results.models import Score
from schedule.models import Round
from live.utils import build_group_tables, build_qualifier_table, build_prequarter_table, build_knockout_tables

STANDARD_ROUND_NAMES = [
    'Group Stage',
    'Qualifier',
    'Pre-Quarter',
    'Quarter',
    'Semi Final',
    'Losers Final',
    'Final',
]

def public_live(request):
    rounds = Round.objects.filter(
        order__in=[1, 2, 3, 4, 5, 6, 7],
        name__in=STANDARD_ROUND_NAMES,
    ).order_by('order')
    current_round = rounds.filter(is_finished=False).first() if rounds.exists() else None
    selected_round = current_round
    selected_round_can_view = bool(
        selected_round and (selected_round.is_finished or (current_round and selected_round.id == current_round.id))
    )
    # Winner for Final round
    winner_team = None
    if selected_round and selected_round.name == 'Final' and selected_round_can_view:
        match = Match.objects.filter(round=selected_round).select_related('team1', 'team2').first()
        if match:
            score = Score.objects.filter(match=match, locked=True).first()
            if score and score.winner:
                winner_team = score.winner
    matches = Match.objects.filter(
        round=selected_round,
    ).select_related('team1', 'team2', 'court', 'round', 'score').order_by('court__id') if selected_round else Match.objects.none()
    group_tables = build_group_tables()
    qualifier_table = build_qualifier_table()
    prequarter_table, prequarter_qualified = build_prequarter_table(rounds, qualifier_table)
    knockout_tables = build_knockout_tables(rounds, prequarter_table)
    quarter_qualified = knockout_tables['quarter_qualified']
    quarter_has_scores = knockout_tables['quarter_has_scores']
    semi_qualified = knockout_tables['semi_qualified']
    semi_has_scores = knockout_tables['semi_has_scores']
    selected_round_can_view = bool(
        selected_round and (selected_round.is_finished or (current_round and selected_round.id == current_round.id))
    )
    # Losers Final point table logic
    losers_final_table = None
    losers_final_has_scores = False
    if selected_round and selected_round.name == 'Losers Final' and selected_round_can_view:
        # Get the locked match for Losers Final
        match = Match.objects.filter(round=selected_round).select_related('team1', 'team2').first()
        if match:
            score = Score.objects.filter(match=match, locked=True).first()
            if score:
                losers_final_has_scores = True
                pf1 = score.team1_score
                pa1 = score.team2_score
                pf2 = score.team2_score
                pa2 = score.team1_score
                pd1 = pf1 - pa1
                pd2 = pf2 - pa2
                losers_final_table = [
                    {
                        'team': match.team1,
                        'points_for': pf1,
                        'points_against': pa1,
                        'points_diff': pd1,
                    },
                    {
                        'team': match.team2,
                        'points_for': pf2,
                        'points_against': pa2,
                        'points_diff': pd2,
                    },
                ]
                losers_final_table.sort(key=lambda row: (row['points_diff'] if row['points_diff'] is not None else float('-inf')), reverse=True)
                # Assign row_class after sorting: first green, second orange
                if len(losers_final_table) > 0:
                    losers_final_table[0]['row_class'] = 'qualified-row'
                if len(losers_final_table) > 1:
                    losers_final_table[1]['row_class'] = 'losers-final-orange-row'
            else:
                losers_final_table = [
                    {
                        'team': match.team1,
                        'points_for': None,
                        'points_against': None,
                        'points_diff': None,
                        'row_class': 'qualified-row',
                    },
                    {
                        'team': match.team2,
                        'points_for': None,
                        'points_against': None,
                        'points_diff': None,
                        'row_class': 'losers-final-orange-row',
                    },
                ]

    context = {
        'matches': matches,
        'group_tables': group_tables,
        'qualifier_table': qualifier_table,
        'rounds': rounds,
        'selected_round': selected_round,
        'selected_round_can_view': selected_round_can_view,
        'current_round': current_round,
        'show_qualifier_rules': current_round and current_round.name == 'Qualifier',
        'prequarter_table': prequarter_table,
        'prequarter_qualified': prequarter_qualified,
        'quarter_qualified': quarter_qualified,
        'quarter_has_scores': quarter_has_scores,
        'semi_qualified': semi_qualified,
        'semi_has_scores': semi_has_scores,
        'losers_final_table': losers_final_table,
        'losers_final_has_scores': losers_final_has_scores,
        'winner_team': winner_team,
    }
    return render(request, 'live/public_live.html', context)

from django.http import JsonResponse
from django.template.loader import render_to_string
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

def public_results_api(request):
    rounds = Round.objects.filter(order__in=[1, 2, 3, 4, 5, 6, 7], name__in=STANDARD_ROUND_NAMES).order_by('order')
    matches = Match.objects.select_related('team1', 'team2', 'court', 'round').filter(round__name__in=STANDARD_ROUND_NAMES).order_by('round__order', 'court__id')
    scores = {s.match_id: s for s in Score.objects.filter(locked=True)}
    round_has_scores = {}
    for match in matches:
        if match.id in scores:
            round_has_scores[match.round_id] = True
    current_round = rounds.filter(is_finished=False).first() if rounds.exists() else None
    group_tables = build_group_tables()
    qualifier_table = build_qualifier_table()
    prequarter_table, prequarter_qualified = build_prequarter_table(rounds, qualifier_table)
    knockout_tables = build_knockout_tables(rounds, prequarter_table)
    quarter_qualified = knockout_tables['quarter_qualified']
    quarter_has_scores = knockout_tables['quarter_has_scores']
    semi_qualified = knockout_tables['semi_qualified']
    semi_has_scores = knockout_tables['semi_has_scores']
    quarter_top = quarter_qualified[:4]
    semi_top = semi_qualified[:2]
    winner_team = None
    runner_up_team = None
    final_round = Round.objects.filter(name__iexact='Final').first()
    if final_round:
        final_match = Match.objects.filter(round=final_round).first()
        final_score = Score.objects.filter(match=final_match, locked=True).first() if final_match else None
        if final_match and final_score and final_score.winner:
            winner_team = final_score.winner
            runner_up_team = final_match.team1 if final_score.winner != final_match.team1 else final_match.team2
    losers_final_table = None
    losers_final_has_scores = False
    losers_round = Round.objects.filter(name__iexact='Losers Final').first()
    if losers_round:
        match = Match.objects.filter(round=losers_round).select_related('team1', 'team2').first()
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

    round_results_html = render_to_string(
        'results/partials/round_results.html',
        {
            'rounds': rounds,
            'matches': matches,
            'scores': scores,
            'group_tables': group_tables,
            'qualifier_table': qualifier_table,
            'prequarter_table': prequarter_table,
            'prequarter_qualified': prequarter_qualified,
            'quarter_qualified': quarter_qualified,
            'quarter_top': quarter_top,
            'quarter_has_scores': quarter_has_scores,
            'semi_top': semi_top,
            'semi_has_scores': semi_has_scores,
            'current_round': current_round,
            'round_has_scores': round_has_scores,
            'winner_team': winner_team,
            'runner_up_team': runner_up_team,
            'losers_final_table': losers_final_table,
            'losers_final_has_scores': losers_final_has_scores,
        },
        request=request,
    )
    placements = {
        'champion': None,
        'runner_up': None,
        'third_place': None,
        'fourth_place': None,
    }
    if final_round:
        final_match = Match.objects.filter(round=final_round).first()
        final_score = Score.objects.filter(match=final_match, locked=True).first() if final_match else None
        if final_match and final_score and final_score.winner:
            placements['champion'] = final_score.winner
            placements['runner_up'] = final_match.team1 if final_score.winner != final_match.team1 else final_match.team2
    if losers_round:
        losers_match = Match.objects.filter(round=losers_round).first()
        losers_score = Score.objects.filter(match=losers_match, locked=True).first() if losers_match else None
        if losers_match and losers_score and losers_score.winner:
            placements['third_place'] = losers_score.winner
            placements['fourth_place'] = losers_match.team1 if losers_score.winner != losers_match.team1 else losers_match.team2
    placements_html = render_to_string(
        'results/partials/placements.html',
        {'placements': placements},
        request=request,
    )
    return JsonResponse({
        'round_results_html': round_results_html,
        'placements_html': placements_html,
        'current_round_id': current_round.id if current_round else None,
    })

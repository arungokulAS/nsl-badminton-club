from collections import defaultdict

from groups.models import Group
from matches.models import Match
from results.models import Score
from schedule.models import Round


def build_group_tables():
    groups = Group.objects.prefetch_related('teams').all().order_by('group_name')
    team_stats = {}
    group_team_ids = defaultdict(list)

    for group in groups:
        for team in group.teams.all():
            team_stats[team.id] = {
                'team': team,
                'played': 0,
                'wins': 0,
                'losses': 0,
                'points': 0,
                'goals_for': 0,
                'goals_against': 0,
                'diff': 0,
            }
            group_team_ids[group.id].append(team.id)

    scores = Score.objects.select_related('match', 'winner', 'match__group', 'match__team1', 'match__team2').filter(
        locked=True,
        match__group__isnull=False,
    )

    for score in scores:
        team1 = score.match.team1
        team2 = score.match.team2
        if team1.id not in team_stats or team2.id not in team_stats:
            continue
        if not score.winner_id:
            continue
        team_stats[team1.id]['goals_for'] += score.team1_score
        team_stats[team1.id]['goals_against'] += score.team2_score
        team_stats[team2.id]['goals_for'] += score.team2_score
        team_stats[team2.id]['goals_against'] += score.team1_score
        team_stats[team1.id]['played'] += 1
        team_stats[team2.id]['played'] += 1
        if score.winner_id == team1.id:
            team_stats[team1.id]['wins'] += 1
            team_stats[team1.id]['points'] += 2
            team_stats[team2.id]['losses'] += 1
        elif score.winner_id == team2.id:
            team_stats[team2.id]['wins'] += 1
            team_stats[team2.id]['points'] += 2
            team_stats[team1.id]['losses'] += 1

    group_tables = []
    for group in groups:
        rows = [team_stats[team_id] for team_id in group_team_ids[group.id]]
        for row in rows:
            row['diff'] = row['goals_for'] - row['goals_against']
        rows.sort(
            key=lambda row: (row['points'], row['diff'], row['goals_for'], row['wins'], row['team'].team_name),
            reverse=True,
        )
        qualified_ids = {row['team'].id for row in rows[:4]}
        for row in rows:
            row['is_qualified'] = row['team'].id in qualified_ids
            row['is_eliminated'] = row['team'].id not in qualified_ids
        group_tables.append({
            'group': group,
            'rows': rows,
        })

    return group_tables


def build_qualifier_table():
    round_obj = Round.objects.filter(name='Qualifier').first()
    if not round_obj:
        return []

    scores = Score.objects.select_related('match', 'winner', 'match__team1', 'match__team2').filter(
        locked=True,
        match__round=round_obj,
    )

    team_stats = {}
    for score in scores:
        team1 = score.match.team1
        team2 = score.match.team2
        for team in (team1, team2):
            if team.id not in team_stats:
                group_name = None
                if team.groups.exists():
                    group_name = team.groups.first().group_name
                    if group_name.lower().startswith('group '):
                        group_name = group_name.split(' ', 1)[1]
                team_stats[team.id] = {
                    'team': team,
                    'group': group_name,
                    'played': 0,
                    'wins': 0,
                    'losses': 0,
                    'points_for': 0,
                    'points_against': 0,
                    'points_diff': 0,
                    'total_points': 0,
                }
        if not score.winner_id:
            continue
        team_stats[team1.id]['played'] += 1
        team_stats[team2.id]['played'] += 1
        team_stats[team1.id]['points_for'] += score.team1_score
        team_stats[team1.id]['points_against'] += score.team2_score
        team_stats[team2.id]['points_for'] += score.team2_score
        team_stats[team2.id]['points_against'] += score.team1_score
        if score.winner_id == team1.id:
            team_stats[team1.id]['wins'] += 1
            team_stats[team1.id]['total_points'] += 2
            team_stats[team2.id]['losses'] += 1
        elif score.winner_id == team2.id:
            team_stats[team2.id]['wins'] += 1
            team_stats[team2.id]['total_points'] += 2
            team_stats[team1.id]['losses'] += 1

    rows = list(team_stats.values())
    for row in rows:
        row['points_diff'] = row['points_for'] - row['points_against']

    winners = [row for row in rows if row['wins'] > 0]
    losers = [row for row in rows if row['wins'] == 0]

    winners_ids = {row['team'].id for row in winners}
    best_losers = sorted(
        losers,
        key=lambda row: (row['points_diff'], row['points_for'], row['team'].team_name),
        reverse=True,
    )[:4]
    best_loser_ids = {row['team'].id for row in best_losers}

    rows.sort(
        key=lambda row: (row['total_points'], row['points_diff'], row['points_for'], row['wins'], row['team'].team_name),
        reverse=True,
    )

    for row in rows:
        row['is_winner'] = row['team'].id in winners_ids
        row['is_best_loser'] = row['team'].id in best_loser_ids
        row['is_eliminated'] = row['team'].id not in winners_ids and row['team'].id not in best_loser_ids

    return rows


def build_prequarter_table(rounds, qualifier_table):
    prequarter_rows = qualifier_table[:16]
    prequarter_table = []
    prequarter_round = rounds.filter(name__icontains='Pre-Quarter').first()
    prequarter_stats = {}
    prequarter_winners = set()
    has_prequarter_scores = False

    if prequarter_round:
        prequarter_scores = Score.objects.select_related('match', 'match__team1', 'match__team2').filter(
            match__round=prequarter_round,
            locked=True,
        )
        for score in prequarter_scores:
            has_prequarter_scores = True
            team1 = score.match.team1
            team2 = score.match.team2
            if score.winner_id:
                prequarter_winners.add(score.winner_id)
            elif team1 and team2:
                if score.team1_score > score.team2_score:
                    prequarter_winners.add(team1.id)
                elif score.team2_score > score.team1_score:
                    prequarter_winners.add(team2.id)
            for team in (team1, team2):
                if team and team.id not in prequarter_stats:
                    prequarter_stats[team.id] = {'pf': 0, 'pa': 0, 'pd': 0}
            if team1 and team2:
                prequarter_stats[team1.id]['pf'] += score.team1_score
                prequarter_stats[team1.id]['pa'] += score.team2_score
                prequarter_stats[team2.id]['pf'] += score.team2_score
                prequarter_stats[team2.id]['pa'] += score.team1_score

    for idx, row in enumerate(prequarter_rows, start=1):
        row_copy = dict(row)
        if has_prequarter_scores:
            stats = prequarter_stats.get(row['team'].id, {'pf': 0, 'pa': 0, 'pd': 0})
            stats['pd'] = stats['pf'] - stats['pa']
            row_copy['points_for'] = stats['pf']
            row_copy['points_against'] = stats['pa']
            row_copy['points_diff'] = stats['pd']
        else:
            row_copy['points_for'] = None
            row_copy['points_against'] = None
            row_copy['points_diff'] = None
        row_copy['rank'] = idx
        row_copy['is_prequarter_winner'] = row['team'].id in prequarter_winners
        row_copy['is_prequarter_qualified'] = idx <= 8
        row_copy['is_prequarter_eliminated'] = idx > 8
        prequarter_table.append(row_copy)

    if has_prequarter_scores:
        prequarter_table.sort(
            key=lambda row: (
                row['is_prequarter_winner'],
                row['points_diff'],
                row['points_for'],
                row['team'].team_name,
            ),
            reverse=True,
        )
        for idx, row in enumerate(prequarter_table, start=1):
            row['rank'] = idx
            row['is_prequarter_qualified'] = row['is_prequarter_winner']
            row['is_prequarter_eliminated'] = not row['is_prequarter_winner']

    prequarter_qualified = [row for row in prequarter_table if row['is_prequarter_qualified']]
    return prequarter_table, prequarter_qualified


def build_knockout_tables(rounds, prequarter_table):
    quarter_qualified = [dict(row) for row in prequarter_table if row.get('is_prequarter_qualified')]
    quarter_round = rounds.filter(name__iexact='Quarter').first()
    quarter_stats = {}
    quarter_has_scores = False
    quarter_winners = set()
    if quarter_round:
        quarter_scores = Score.objects.select_related('match', 'match__team1', 'match__team2').filter(
            match__round=quarter_round,
            locked=True,
        )
        for score in quarter_scores:
            quarter_has_scores = True
            team1 = score.match.team1
            team2 = score.match.team2
            if score.winner_id:
                quarter_winners.add(score.winner_id)
            elif team1 and team2:
                if score.team1_score > score.team2_score:
                    quarter_winners.add(team1.id)
                elif score.team2_score > score.team1_score:
                    quarter_winners.add(team2.id)
            for team in (team1, team2):
                if team and team.id not in quarter_stats:
                    quarter_stats[team.id] = {'pf': 0, 'pa': 0, 'pd': 0}
            if team1 and team2:
                quarter_stats[team1.id]['pf'] += score.team1_score
                quarter_stats[team1.id]['pa'] += score.team2_score
                quarter_stats[team2.id]['pf'] += score.team2_score
                quarter_stats[team2.id]['pa'] += score.team1_score

    for row in quarter_qualified:
        if quarter_has_scores:
            stats = quarter_stats.get(row['team'].id, {'pf': 0, 'pa': 0, 'pd': 0})
            stats['pd'] = stats['pf'] - stats['pa']
            row['points_for'] = stats['pf']
            row['points_against'] = stats['pa']
            row['points_diff'] = stats['pd']
        else:
            row['points_for'] = None
            row['points_against'] = None
            row['points_diff'] = None
    quarter_qualified.sort(
        key=lambda row: (
            row['points_diff'] if row['points_diff'] is not None else float('-inf'),
            row['points_for'] if row['points_for'] is not None else float('-inf'),
            row['team'].team_name,
        ),
        reverse=True,
    )
    for idx, row in enumerate(quarter_qualified, start=1):
        row['is_quarter_top'] = idx <= 4
        row['is_quarter_eliminated'] = idx > 4

    semi_qualified = [dict(row) for row in quarter_qualified if row.get('team') and row['team'].id in quarter_winners]
    semi_round = rounds.filter(name__iexact='Semi Final').first()
    semi_stats = {}
    semi_has_scores = False
    semi_round_teams = []
    if semi_round:
        semi_matches = Match.objects.select_related('team1', 'team2').filter(round=semi_round)
        for match in semi_matches:
            for team in (match.team1, match.team2):
                if team and team not in semi_round_teams:
                    semi_round_teams.append(team)
        semi_scores = Score.objects.select_related('match', 'match__team1', 'match__team2').filter(
            match__round=semi_round,
            locked=True,
        )
        for score in semi_scores:
            semi_has_scores = True
            team1 = score.match.team1
            team2 = score.match.team2
            for team in (team1, team2):
                if team and team.id not in semi_stats:
                    semi_stats[team.id] = {'pf': 0, 'pa': 0, 'pd': 0}
            if team1 and team2:
                semi_stats[team1.id]['pf'] += score.team1_score
                semi_stats[team1.id]['pa'] += score.team2_score
                semi_stats[team2.id]['pf'] += score.team2_score
                semi_stats[team2.id]['pa'] += score.team1_score

    if not semi_qualified and semi_round_teams:
        semi_qualified = [{'team': team} for team in semi_round_teams]

    for row in semi_qualified:
        if semi_has_scores:
            stats = semi_stats.get(row['team'].id, {'pf': 0, 'pa': 0, 'pd': 0})
            stats['pd'] = stats['pf'] - stats['pa']
            row['points_for'] = stats['pf']
            row['points_against'] = stats['pa']
            row['points_diff'] = stats['pd']
        else:
            row['points_for'] = None
            row['points_against'] = None
            row['points_diff'] = None
    semi_qualified.sort(
        key=lambda row: (
            row['points_diff'] if row['points_diff'] is not None else float('-inf'),
            row['points_for'] if row['points_for'] is not None else float('-inf'),
            row['team'].team_name,
        ),
        reverse=True,
    )
    for idx, row in enumerate(semi_qualified, start=1):
        row['is_semi_top'] = idx <= 2
        row['is_semi_eliminated'] = idx > 2

    return {
        'quarter_qualified': quarter_qualified,
        'quarter_has_scores': quarter_has_scores,
        'semi_qualified': semi_qualified,
        'semi_has_scores': semi_has_scores,
    }

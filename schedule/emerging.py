from dataclasses import dataclass
from typing import List, Dict, Any

from django.db import transaction

from matches.models import Match
from results.models import Score
from schedule.models import Round, Court


EMERGING_ROUND_CONFIG = [
    ('Emerging Quarter', 101),
    ('Emerging Semi Final', 102),
    ('Emerging Final', 103),
]


@dataclass
class EmergingSeed:
    team: object
    diff: int
    points_for: int


def ensure_emerging_rounds(points_per_set: int = 15, sets_per_match: int = 1) -> List[Round]:
    rounds = []
    for name, order in EMERGING_ROUND_CONFIG:
        round_obj, _ = Round.objects.get_or_create(
            name=name,
            defaults={
                'order': order,
                'points_per_set': points_per_set,
                'sets_per_match': sets_per_match,
                'settings_locked': True,
                'is_finished': False,
            },
        )
        updated = False
        if round_obj.order != order:
            round_obj.order = order
            updated = True
        if round_obj.points_per_set != points_per_set:
            round_obj.points_per_set = points_per_set
            updated = True
        if round_obj.sets_per_match != sets_per_match:
            round_obj.sets_per_match = sets_per_match
            updated = True
        if not round_obj.settings_locked:
            round_obj.settings_locked = True
            updated = True
        if updated:
            round_obj.save(update_fields=['order', 'points_per_set', 'sets_per_match', 'settings_locked'])
        rounds.append(round_obj)
    return sorted(rounds, key=lambda r: r.order)


def compute_bottom_eight_from_group_stage() -> List[EmergingSeed]:
    scores = Score.objects.select_related('match', 'match__team1', 'match__team2').filter(
        locked=True,
        match__round__name='Group Stage',
        match__round__order=1,
    )

    stats: Dict[int, Dict[str, Any]] = {}
    for score in scores:
        team1 = score.match.team1
        team2 = score.match.team2
        if not team1 or not team2:
            continue

        if team1.id not in stats:
            stats[team1.id] = {'team': team1, 'pf': 0, 'pa': 0}
        if team2.id not in stats:
            stats[team2.id] = {'team': team2, 'pf': 0, 'pa': 0}

        stats[team1.id]['pf'] += score.team1_score
        stats[team1.id]['pa'] += score.team2_score
        stats[team2.id]['pf'] += score.team2_score
        stats[team2.id]['pa'] += score.team1_score

    rows = []
    for row in stats.values():
        diff = row['pf'] - row['pa']
        rows.append(EmergingSeed(team=row['team'], diff=diff, points_for=row['pf']))

    rows.sort(key=lambda r: (r.diff, r.points_for, r.team.team_name))
    return rows[:8]


def _select_courts() -> List[Court]:
    courts = list(Court.objects.all().order_by('id'))
    return courts


def generate_emerging_bracket(force: bool = False) -> Dict[str, Any]:
    rounds = ensure_emerging_rounds()
    quarter_round = rounds[0]

    if Match.objects.filter(round=quarter_round).exists() and not force:
        return {'created': False, 'message': 'Emerging Quarter already exists. Use force to regenerate.'}

    with transaction.atomic():
        if force:
            Match.objects.filter(round__name__in=[name for name, _ in EMERGING_ROUND_CONFIG]).delete()
            Round.objects.filter(name__in=[name for name, _ in EMERGING_ROUND_CONFIG]).update(is_finished=False)

        seeds = compute_bottom_eight_from_group_stage()
        if len(seeds) < 8:
            return {'created': False, 'message': 'Need at least 8 teams with locked Group Stage scores.'}

        courts = _select_courts()
        pairings = [
            (seeds[0].team, seeds[7].team),
            (seeds[1].team, seeds[6].team),
            (seeds[2].team, seeds[5].team),
            (seeds[3].team, seeds[4].team),
        ]

        for index, (team1, team2) in enumerate(pairings):
            court = courts[index % len(courts)] if courts else None
            Match.objects.create(
                round=quarter_round,
                team1=team1,
                team2=team2,
                court=court,
                status='scheduled',
            )

    return {'created': True, 'message': 'Emerging Quarter generated.', 'teams': [seed.team.team_name for seed in seeds]}


def advance_emerging_rounds() -> Dict[str, Any]:
    rounds = ensure_emerging_rounds()
    quarter_round, semi_round, final_round = rounds
    courts = _select_courts()

    if Match.objects.filter(round=quarter_round).exists() and not Match.objects.filter(round=semi_round).exists():
        quarter_matches = Match.objects.filter(round=quarter_round).order_by('id')
        winners = []
        for match in quarter_matches:
            score = Score.objects.filter(match=match, locked=True, winner__isnull=False).first()
            if score and score.winner:
                winners.append(score.winner)
        if len(winners) == 4:
            with transaction.atomic():
                pairings = [
                    (winners[0], winners[3]),
                    (winners[1], winners[2]),
                ]
                for index, (team1, team2) in enumerate(pairings):
                    court = courts[index % len(courts)] if courts else None
                    Match.objects.create(
                        round=semi_round,
                        team1=team1,
                        team2=team2,
                        court=court,
                        status='scheduled',
                    )
            return {'advanced': True, 'message': 'Emerging Semi Final generated.'}
        return {'advanced': False, 'message': 'Emerging Quarter is not fully completed/locked yet.'}

    if Match.objects.filter(round=semi_round).exists() and not Match.objects.filter(round=final_round).exists():
        semi_matches = Match.objects.filter(round=semi_round).order_by('id')
        winners = []
        for match in semi_matches:
            score = Score.objects.filter(match=match, locked=True, winner__isnull=False).first()
            if score and score.winner:
                winners.append(score.winner)
        if len(winners) == 2:
            with transaction.atomic():
                court = courts[0] if courts else None
                Match.objects.create(
                    round=final_round,
                    team1=winners[0],
                    team2=winners[1],
                    court=court,
                    status='scheduled',
                )
            return {'advanced': True, 'message': 'Emerging Final generated.'}
        return {'advanced': False, 'message': 'Emerging Semi Final is not fully completed/locked yet.'}

    return {'advanced': False, 'message': 'No advancement needed right now.'}

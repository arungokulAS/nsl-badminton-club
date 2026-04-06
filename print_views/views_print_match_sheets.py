from django.shortcuts import render
from schedule.models import Round, Court
from matches.models import Match

def print_match_sheets(request):
    score_options = [15, 21, 30]
    blank_points_raw = request.GET.get('blank_points', '').strip()
    blank_points = int(blank_points_raw) if blank_points_raw in {'15', '21', '30'} else None
    blank_sheet = None
    if blank_points:
        blank_sheet = {
            'points': blank_points,
            'rows': range(1, blank_points + 1),
        }

    group_stage_round = Round.objects.filter(name='Group Stage').first()
    group_stage_points = group_stage_round.points_per_set if group_stage_round else 21
    fetch_prefill = request.GET.get('fetch_prefill') == '1'

    prefill_courts = []
    court_slots = list(Court.objects.all().order_by('id')[:4])
    while len(court_slots) < 4:
        slot_index = len(court_slots) + 1
        court_slots.append(type('CourtSlot', (), {'id': slot_index, 'name': f'Court {slot_index}'})())

    matches_queryset = Match.objects.none()
    if fetch_prefill and group_stage_round:
        matches_queryset = Match.objects.select_related('team1', 'team2', 'court', 'round', 'group').filter(
            round=group_stage_round
        ).order_by('court__id', 'id')

    matches_by_court_id = {}
    for match in matches_queryset:
        if match.court_id not in matches_by_court_id:
            matches_by_court_id[match.court_id] = []
        matches_by_court_id[match.court_id].append(match)

    for court_slot in court_slots:
        court_matches = []
        raw_matches = matches_by_court_id.get(court_slot.id, [])
        for match_index, match in enumerate(raw_matches, start=1):
            court_matches.append(
                {
                    'match_no': match_index,
                    'group_name': match.group.group_name if match.group else '-',
                    'team1_name': match.team1.team_name if match.team1 else '-',
                    'team2_name': match.team2.team_name if match.team2 else '-',
                    'points': group_stage_points,
                    'rows': range(1, group_stage_points + 1),
                }
            )
        prefill_courts.append(
            {
                'court_name': court_slot.name,
                'court_id': court_slot.id,
                'matches': court_matches,
            }
        )

    context = {
        'score_options': score_options,
        'blank_points': blank_points,
        'blank_sheet': blank_sheet,
        'group_stage_points': group_stage_points,
        'group_stage_settings_locked': bool(group_stage_round.settings_locked) if group_stage_round else False,
        'fetch_prefill': fetch_prefill,
        'prefill_courts': prefill_courts,
    }
    return render(request, 'print_views/print_match_sheets.html', context)

from io import BytesIO

from django.http import HttpResponse
from openpyxl import Workbook

from groups.models import Group
from matches.models import Match
from schedule.models import Round
from teams.models import Team


def download_team_list_xlsx(request):
    teams = Team.objects.all().order_by('team_name')
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = 'Teams'
    sheet.append(['#', 'Team', 'Player 1', 'Player 2'])
    for idx, team in enumerate(teams, start=1):
        sheet.append([idx, team.team_name, team.player1_name, team.player2_name])

    output = BytesIO()
    workbook.save(output)
    output.seek(0)
    response = HttpResponse(
        output.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )
    response['Content-Disposition'] = 'attachment; filename="team_list.xlsx"'
    return response


def download_group_list_xlsx(request):
    groups = Group.objects.prefetch_related('teams').all().order_by('group_name')
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = 'Groups'
    sheet.append(['Group', 'Team', 'Player 1', 'Player 2'])
    for group in groups:
        for team in group.teams.all().order_by('team_name'):
            sheet.append([group.group_name, team.team_name, team.player1_name, team.player2_name])

    output = BytesIO()
    workbook.save(output)
    output.seek(0)
    response = HttpResponse(
        output.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )
    response['Content-Disposition'] = 'attachment; filename="group_list.xlsx"'
    return response


def download_schedule_xlsx(request):
    standard_round_names = [
        'Group Stage',
        'Qualifier',
        'Pre-Quarter',
        'Quarter',
        'Semi Final',
        'Losers Final',
        'Final',
    ]
    rounds = Round.objects.filter(order__in=[1, 2, 3, 4, 5, 6, 7], name__in=standard_round_names).order_by('order')
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = 'Schedule'
    sheet.append(['Round', 'Group', 'Court', 'Team 1', 'Team 2', 'Status'])
    for round_obj in rounds:
        matches = Match.objects.select_related('team1', 'team2', 'court', 'group').filter(round=round_obj).order_by('court__id', 'id')
        for match in matches:
            sheet.append([
                round_obj.name,
                match.group.group_name if match.group else '-',
                match.court.name if match.court else '-',
                match.team1.team_name if match.team1 else '-',
                match.team2.team_name if match.team2 else '-',
                match.status,
            ])

    output = BytesIO()
    workbook.save(output)
    output.seek(0)
    response = HttpResponse(
        output.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )
    response['Content-Disposition'] = 'attachment; filename="schedule.xlsx"'
    return response

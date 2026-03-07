from io import BytesIO

from django.http import HttpResponse
from openpyxl import Workbook

from groups.models import Group
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

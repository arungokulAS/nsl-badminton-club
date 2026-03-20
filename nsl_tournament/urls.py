"""
URL configuration for nsl_tournament project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from accounts.views import admin_login, admin_logout, admin_dashboard
from django.shortcuts import render

from teams.views import admin_teams
from groups.views import admin_groups
from schedule.views import admin_schedule
from referee.views import admin_live_manage
from schedule.views_finish_round import admin_finish_round
from results.views_public import public_results
from results.views_public_api import public_results_api
from schedule.views_public import public_schedule
from teams.views_public import public_teams
from groups.views_public import public_groups
from live.views_public import public_live
from live.views_public_api import public_live_api
from print_views.views_print import print_bracket
from print_views.views_print_team_list import print_team_list
from print_views.views_print_match_sheets import print_match_sheets
from print_views.views_print_group_standings import print_group_standings
from print_views.views_print_referee_assignments import print_referee_assignments
from print_views.views_print_schedule_overview import print_schedule_overview
from print_views.views_print_emerging_teams import print_emerging_teams
from print_views.views_print_downloads import download_group_list_xlsx, download_team_list_xlsx, download_schedule_xlsx, download_schedule_court_xlsx
from core.views_public import public_referee, public_contact, print_menu

urlpatterns = [
    # Home page
    path('', lambda request: render(request, 'home.html'), name='home'),
    path('admin/login', admin_login, name='admin_login'),
    path('admin/logout', admin_logout, name='admin_logout'),
    path('admin/dashboard', admin_dashboard, name='admin_dashboard'),
    path('admin/teams', admin_teams, name='admin_teams'),
    path('admin/groups', admin_groups, name='admin_groups'),
    path('admin/schedule', admin_schedule, name='admin_schedule'),
    path('admin/live-manage', admin_live_manage, name='admin_live_manage'),
    path('admin/finish-round', admin_finish_round, name='admin_finish_round'),
    path('tournament/results', public_results, name='public_results'),
    path('tournament/results/api', public_results_api, name='public_results_api'),
    path('tournament/schedule', public_schedule, name='public_schedule'),
    path('tournament/teams', public_teams, name='public_teams'),
    path('tournament/groups', public_groups, name='public_groups'),
    path('tournament/live', public_live, name='public_live'),
    path('tournament/live/api', public_live_api, name='public_live_api'),
    path('referee', public_referee, name='public_referee'),
    path('referee/', include('referee.urls')),
    path('contact', public_contact, name='public_contact'),
    path('print/team', print_menu, name='print_menu'),
    path('print/bracket', print_bracket, name='print_bracket'),
    path('print/teams', print_team_list, name='print_team_list'),
    path('print/teams.xlsx', download_team_list_xlsx, name='download_team_list_xlsx'),
    path('print/matches', print_match_sheets, name='print_match_sheets'),
    path('print/groups', print_group_standings, name='print_group_standings'),
    path('print/emerging-teams', print_emerging_teams, name='print_emerging_teams'),
    path('print/groups.xlsx', download_group_list_xlsx, name='download_group_list_xlsx'),
    path('print/referees', print_referee_assignments, name='print_referee_assignments'),
    path('print/schedule', print_schedule_overview, name='print_schedule_overview'),
    path('print/schedule.xlsx', download_schedule_xlsx, name='download_schedule_xlsx'),
    path('print/schedule/<int:round_id>/<str:court_key>.xlsx', download_schedule_court_xlsx, name='download_schedule_court_xlsx'),
    path('admin/', admin.site.urls),
]

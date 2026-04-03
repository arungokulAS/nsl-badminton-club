import csv
from io import TextIOWrapper
from django.shortcuts import render, redirect
from django.contrib import messages
from .models import Team
from core.models import TournamentRegistration

def admin_teams(request):
	if not request.session.get('is_admin'):
		return redirect('/admin/login')
	teams = Team.objects.all().order_by('id')
	is_locked = teams.first().is_locked if teams.exists() else False

	# Manual add
	if request.method == 'POST' and 'add_team' in request.POST and not is_locked:
		p1 = request.POST.get('player1_name', '').strip()
		p2 = request.POST.get('player2_name', '').strip()
		if p1 and p2:
			team_name = f"{p1} & {p2}"
			if not Team.objects.filter(team_name=team_name).exists():
				Team.objects.create(player1_name=p1, player2_name=p2, team_name=team_name)
			else:
				messages.error(request, 'Duplicate team name.')
		else:
			messages.error(request, 'Both player names are required.')
		return redirect('/admin/teams')

	# CSV upload
	if request.method == 'POST' and 'upload_csv' in request.POST and not is_locked:
		csv_file = request.FILES.get('csv_file')
		if csv_file:
			try:
				wrapper = TextIOWrapper(csv_file, encoding='utf-8')
				# Try DictReader first (headered)
				csv_reader = csv.DictReader(wrapper)
				added = 0
				skipped = 0
				if csv_reader.fieldnames and 'player1_name' in csv_reader.fieldnames and 'player2_name' in csv_reader.fieldnames:
					for row in csv_reader:
						p1 = row.get('player1_name', '').strip()
						p2 = row.get('player2_name', '').strip()
						if p1 and p2:
							team_name = f"{p1} & {p2}"
							if not Team.objects.filter(team_name=team_name).exists():
								Team.objects.create(player1_name=p1, player2_name=p2, team_name=team_name)
								added += 1
							else:
								skipped += 1
						else:
							skipped += 1
				else:
					# No headers, fallback to reader
					wrapper.seek(0)
					csv_reader = csv.reader(wrapper)
					for row in csv_reader:
						if len(row) >= 2:
							p1 = row[0].strip()
							p2 = row[1].strip()
							if p1 and p2:
								team_name = f"{p1} & {p2}"
								if not Team.objects.filter(team_name=team_name).exists():
									Team.objects.create(player1_name=p1, player2_name=p2, team_name=team_name)
									added += 1
								else:
									skipped += 1
							else:
								skipped += 1
						else:
							skipped += 1
				if added:
					messages.success(request, f'Upload successful: {added} teams added, {skipped} skipped.')
				else:
					messages.error(request, 'No valid teams added. Check CSV format.')
			except Exception as e:
				messages.error(request, f'Invalid CSV format: {e}')
		else:
			messages.error(request, 'No CSV file selected.')
		return redirect('/admin/teams')

	# Import from registration forms
	if request.method == 'POST' and 'from_forms' in request.POST and not is_locked:
		registrations = TournamentRegistration.objects.all().order_by('-created_at')
		added = 0
		skipped = 0
		for registration in registrations:
			player1_name = f"{registration.player1_first_name} {registration.player1_last_name}".strip()
			player2_name = f"{registration.player2_first_name} {registration.player2_last_name}".strip()
			if not player1_name or not player2_name:
				skipped += 1
				continue
			team_name = f"{player1_name} & {player2_name}"
			if Team.objects.filter(team_name=team_name).exists():
				skipped += 1
				continue
			Team.objects.create(
				player1_name=player1_name,
				player2_name=player2_name,
				team_name=team_name,
			)
			added += 1
		if added:
			messages.success(request, f'Imported {added} teams from registration forms. {skipped} skipped.')
		else:
			messages.error(request, 'No new teams imported from registration forms.')
		return redirect('/admin/teams')

	# Edit
	if request.method == 'POST' and 'edit_team' in request.POST and not is_locked:
		team_id = request.POST.get('team_id')
		p1 = request.POST.get('player1_name', '').strip()
		p2 = request.POST.get('player2_name', '').strip()
		if team_id and p1 and p2:
			team = Team.objects.get(id=team_id)
			team.player1_name = p1
			team.player2_name = p2
			team.team_name = f"{p1} & {p2}"
			team.save()
		return redirect('/admin/teams')

	# Delete
	if request.method == 'POST' and 'delete_team' in request.POST and not is_locked:
		team_id = request.POST.get('team_id')
		if team_id:
			Team.objects.filter(id=team_id).delete()
		return redirect('/admin/teams')

	# Clear all
	if request.method == 'POST' and 'clear_all' in request.POST and not is_locked:
		Team.objects.all().delete()
		return redirect('/admin/teams')

	# Lock teams
	if request.method == 'POST' and 'lock_teams' in request.POST and not is_locked:
		password = request.POST.get('admin_password')
		import os
		admin_password = os.environ.get('ADMIN_PASSWORD', 'admin123')
		if password == admin_password:
			Team.objects.all().update(is_locked=True)
		else:
			messages.error(request, 'Invalid admin password.')
		return redirect('/admin/teams')

	# Unlock teams
	if request.method == 'POST' and 'unlock_teams' in request.POST and is_locked:
		password = request.POST.get('admin_password')
		import os
		admin_password = os.environ.get('ADMIN_PASSWORD', 'admin123')
		if password == admin_password:
			Team.objects.all().update(is_locked=False)
			# Clear groups and matches for consistency
			from groups.models import Group
			from matches.models import Match
			from schedule.models import Round
			Group.objects.all().delete()
			Match.objects.all().delete()
			Round.objects.filter(order__in=[1, 2, 3, 4, 5, 6, 7]).update(
				is_finished=False,
				settings_locked=False,
				points_per_set=21,
				sets_per_match=1,
			)
			request.session['locked_num_courts'] = None
			messages.success(request, 'Teams unlocked. Please recreate groups and schedule.')
		else:
			messages.error(request, 'Invalid admin password.')
		return redirect('/admin/teams')

	teams = Team.objects.all().order_by('id')
	is_locked = teams.first().is_locked if teams.exists() else False
	return render(request, 'teams/admin_teams.html', {'teams': teams, 'is_locked': is_locked})

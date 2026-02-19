import random
from django.shortcuts import render, redirect
from django.contrib import messages
from teams.models import Team
from .models import Group

def admin_groups(request):
	if not request.session.get('is_admin'):
		return redirect('/admin/login')
	locked_teams = Team.objects.filter(is_locked=True)
	groups = Group.objects.all().order_by('group_name')
	is_locked = groups.first().is_locked if groups.exists() else False


	# Step 1: Create groups (no locking yet)
	if request.method == 'POST' and 'create_groups' in request.POST and not is_locked and not groups.exists():
		num_groups = int(request.POST.get('num_groups', 0))
		if num_groups < 1 or num_groups > 10 or locked_teams.count() < num_groups:
			messages.error(request, 'Invalid group count or not enough teams.')
			return redirect('/admin/groups')
		# Shuffle and distribute teams
		team_list = list(locked_teams)
		random.shuffle(team_list)
		Group.objects.all().delete()
		for i in range(num_groups):
			group = Group.objects.create(group_name=chr(65+i), is_locked=False)
			group.teams.set([])
		for idx, team in enumerate(team_list):
			group = Group.objects.get(group_name=chr(65 + (idx % num_groups)))
			group.teams.add(team)
		messages.success(request, 'Groups created. You can now move teams and lock groups.')
		return redirect('/admin/groups')

	# Step 2: Move team between groups before locking
	if request.method == 'POST' and 'move_team' in request.POST and not is_locked and groups.exists():
		move_team_id = request.POST.get('move_team_id')
		target_group_id = request.POST.get('target_group')
		if move_team_id and target_group_id:
			try:
				from django.db import transaction
				with transaction.atomic():
					team = Team.objects.get(id=move_team_id)
					# Remove from all groups
					for group in Group.objects.filter(teams=team):
						group.teams.remove(team)
					# Add to target group
					target_group = Group.objects.get(id=target_group_id)
					target_group.teams.add(team)
				messages.success(request, 'Team moved successfully.')
			except Exception as e:
				messages.error(request, f'Error moving team: {e}')
		else:
			messages.error(request, 'Please select both team and group.')
		return redirect('/admin/groups')

	# Step 3: Lock groups
	if request.method == 'POST' and 'lock_groups' in request.POST and not is_locked and groups.exists():
		password = request.POST.get('admin_password')
		import os
		admin_password = os.environ.get('ADMIN_PASSWORD', 'admin123')
		if password != admin_password:
			messages.error(request, 'Invalid admin password.')
			return redirect('/admin/groups')
		for group in groups:
			group.is_locked = True
			group.save()
		messages.success(request, 'Groups locked.')
		return redirect('/admin/groups')

	return render(request, 'groups/admin_groups.html', {
		'locked_teams': locked_teams,
		'groups': groups,
		'is_locked': is_locked,
		'group_range': range(1, 11)
	})

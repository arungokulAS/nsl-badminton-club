

from django.shortcuts import render, redirect
from django.contrib import messages
from schedule.models import Round, Court
from matches.models import Match
from groups.models import Group
from teams.models import Team
import os
import random

def admin_schedule(request):
	if not request.session.get('is_admin'):
		return redirect('/admin/login')

	rounds = Round.objects.all().order_by('order')
	# Lock court count after admin confirmation
	if 'unlock_courts' in request.POST and request.method == 'POST':
		if request.POST.get('admin_password') == 'admin123':  # Replace with your admin password logic
			request.session['locked_num_courts'] = None
			messages.success(request, 'Court selection unlocked. You can now select a new number of courts.')
			return redirect('/admin/schedule')
		else:
			messages.error(request, 'Invalid admin password.')
			return redirect('/admin/schedule')

	locked_num_courts = request.session.get('locked_num_courts')
	num_courts_selected = None
	if locked_num_courts:
		num_courts_selected = locked_num_courts
	elif request.method == 'POST' and 'generate_schedule' in request.POST:
		num_courts_selected = int(request.POST.get('num_courts', 0))
		# Lock the court count
		request.session['locked_num_courts'] = num_courts_selected
	courts = Court.objects.all().order_by('id')
	if num_courts_selected:
		courts = list(courts[:num_courts_selected])
	else:
		courts = list(courts)
	groups = Group.objects.all().order_by('group_name')
	matches = Match.objects.select_related('round', 'court', 'team1', 'team2').all().order_by('round__order', 'court__id')
	# Only allow up to the number of actual Court objects
	court_range = range(1, len(courts) + 1)


	from django.db import transaction
	next_round = rounds.filter(is_finished=False).order_by('order').first() if rounds.exists() else None

	if request.method == 'POST' and 'generate_schedule' in request.POST and next_round:
		requested_round_id = int(request.POST.get('round', 0))
		num_courts = len(courts)
		if not courts:
			messages.error(request, 'No courts defined.')
			return redirect('/admin/schedule')
		if int(request.POST.get('num_courts', 0)) > Court.objects.count():
			messages.error(request, 'Invalid number of courts.')
			return redirect('/admin/schedule')
		if requested_round_id != next_round.id:
			messages.error(request, 'You can only schedule the next unfinished round.')
			return redirect('/admin/schedule')
		# Prevent duplicate schedule for the same round
		if Match.objects.filter(round_id=requested_round_id).exists():
			messages.error(request, 'Schedule for this round already exists.')
			return redirect('/admin/schedule')
		# Always delete existing matches for this round before generating new schedule (should be redundant now)
		Match.objects.filter(round_id=requested_round_id).delete()
		round_id = requested_round_id
		# Group Stage
		if next_round.order == 1 and groups.exists():
			def generate_group_matches(group_teams):
				matches = []
				for i in range(len(group_teams)):
					for j in range(i+1, len(group_teams)):
						matches.append((group_teams[i], group_teams[j]))
				return matches

			import logging
			from collections import deque
			logger = logging.getLogger("schedule_debug")
			with transaction.atomic():
				# Define group-to-court mapping and slot rotation
				group_court_map = {
					1: [0, 4],  # Court 1: Group A, E
					2: [1, 4],  # Court 2: Group B, E
					3: [2, 5],  # Court 3: Group C, F
					4: [3, 5],  # Court 4: Group D, F
				}
				group_names = [g.group_name for g in groups]
				# Map 'A', 'B', ... to Group objects
				group_objs = {}
				for g in groups:
					code = g.group_name.strip().upper()
					if code.startswith('GROUP '):
						code = code.replace('GROUP ', '')
					group_objs[code] = g
				# Build matches for each group
				group_matches = {}
				for g in group_names:
					teams = list(group_objs[g].teams.all())
					matches = [(g, m[0], m[1]) for m in generate_group_matches(teams)]
					random.shuffle(matches)
					group_matches[g] = deque(matches)
				# Prepare per-court match queues with slot-based rotation
				court_slots = [[] for _ in courts]
				slot_idx = 0
				max_slots = max(len(m) for m in group_matches.values()) * 2  # Enough slots for all
				for slot in range(max_slots):
					for cidx, court in enumerate(courts):
						if cidx+1 not in group_court_map:
							continue
						g1_idx, g2_idx = group_court_map[cidx+1]
						g1 = chr(65+g1_idx)  # 'A', 'B', ...
						g2 = chr(65+g2_idx)
						# Alternate between the two groups for this court
						group_for_slot = g1 if slot % 2 == 0 else g2
						if group_for_slot in group_matches and group_matches[group_for_slot]:
							court_slots[cidx].append(group_matches[group_for_slot].popleft())
				# Flatten all court slots into a master schedule with rest enforcement
				master_schedule = []
				team_last_slot = {}
				slot_pointer = [0]*len(courts)
				total_slots = max(len(slots) for slots in court_slots)
				for slot in range(total_slots):
					for cidx, court in enumerate(courts):
						if slot_pointer[cidx] < len(court_slots[cidx]):
							group, team1, team2 = court_slots[cidx][slot_pointer[cidx]]
							# Enforce rest: no team plays 3 consecutive matches
							last1 = team_last_slot.get(team1.id, -100)
							last2 = team_last_slot.get(team2.id, -100)
							if len(master_schedule) - last1 < 2 or len(master_schedule) - last2 < 2:
								# Push to next available slot
								court_slots[cidx].append((group, team1, team2))
								slot_pointer[cidx] += 1
								continue
							master_schedule.append((court, group, team1, team2))
							team_last_slot[team1.id] = len(master_schedule)
							team_last_slot[team2.id] = len(master_schedule)
							slot_pointer[cidx] += 1
				# Schedule matches
				for court, group, team1, team2 in master_schedule:
					group_obj = group_objs.get(group)
					Match.objects.create(
						round=next_round,
						group=group_obj,
						team1=team1,
						team2=team2,
						court=court,
						status='scheduled'
					)
			messages.success(request, f'Schedule generated for {next_round.name} with slot-based group/court allocation and rest enforcement.')
		# Qualifier
		elif next_round.order == 2:
			# Get top 4 teams from each group
			from results.models import Score
			qualified_teams = []
			for group in groups:
				group_teams = list(group.teams.all())
				# Sort by group results (score, point diff, etc.)
				group_scores = [Score.objects.filter(match__team1=t).first() for t in group_teams]
				group_scores = [s for s in group_scores if s]
				group_scores.sort(key=lambda s: (s.team1_score + s.team2_score), reverse=True)
				qualified_teams.extend([s.match.team1 for s in group_scores[:4]])
			# Cross-group pairing
			pairings = [
				('A', 'F'), ('B', 'E'), ('C', 'D')
			]
			matches = []
			for g1, g2 in pairings:
				teams1 = [t for t in qualified_teams if t.groups.filter(group_name=g1).exists()]
				teams2 = [t for t in qualified_teams if t.groups.filter(group_name=g2).exists()]
				for i in range(4):
					matches.append((teams1[i], teams2[3-i]))
			random.shuffle(matches)
			with transaction.atomic():
				for idx, (team1, team2) in enumerate(matches):
					court = courts[idx % len(courts)]
					Match.objects.create(
						round=next_round,
						team1=team1,
						team2=team2,
						court=court,
						status='scheduled'
					)
			messages.success(request, f'Qualifier round scheduled.')
		# Pre-Quarter
		elif next_round.order == 3:
			# 12 qualifier winners + 4 best losers
			from results.models import Score
			qualifier_matches = Match.objects.filter(round__order=2)
			winners = [Score.objects.filter(match=m, winner__isnull=False).first().winner for m in qualifier_matches if Score.objects.filter(match=m, winner__isnull=False).first()]
			losers = [m.team1 if Score.objects.filter(match=m).first().winner != m.team1 else m.team2 for m in qualifier_matches if Score.objects.filter(match=m).first()]
			# Rank losers
			best_losers = sorted(losers, key=lambda t: (Score.objects.filter(match__team1=t).first().team1_score + Score.objects.filter(match__team2=t).first().team2_score), reverse=True)[:4]
			teams = winners + best_losers
			# High-vs-low seeding
			teams.sort(key=lambda t: t.team_name)
			pairings = [(teams[i], teams[-(i+1)]) for i in range(8)]
			with transaction.atomic():
				for idx, (team1, team2) in enumerate(pairings):
					court = courts[idx % len(courts)]
					Match.objects.create(
						round=next_round,
						team1=team1,
						team2=team2,
						court=court,
						status='scheduled'
					)
			messages.success(request, f'Pre-Quarter round scheduled.')
		# Quarter
		elif next_round.order == 4:
			# 8 teams, knockout
			from results.models import Score
			preq_matches = Match.objects.filter(round__order=3)
			winners = [Score.objects.filter(match=m, winner__isnull=False).first().winner for m in preq_matches if Score.objects.filter(match=m, winner__isnull=False).first()]
			random.shuffle(winners)
			with transaction.atomic():
				for idx in range(0, len(winners), 2):
					if idx+1 < len(winners):
						court = courts[(idx//2) % len(courts)]
						Match.objects.create(
							round=next_round,
							team1=winners[idx],
							team2=winners[idx+1],
							court=court,
							status='scheduled'
						)
			messages.success(request, f'Quarter-Final round scheduled.')
		# Semi
		elif next_round.order == 5:
			# 4 teams, knockout
			from results.models import Score
			q_matches = Match.objects.filter(round__order=4)
			winners = [Score.objects.filter(match=m, winner__isnull=False).first().winner for m in q_matches if Score.objects.filter(match=m, winner__isnull=False).first()]
			with transaction.atomic():
				for idx in range(0, len(winners), 2):
					if idx+1 < len(winners):
						court = courts[(idx//2) % len(courts)]
						Match.objects.create(
							round=next_round,
							team1=winners[idx],
							team2=winners[idx+1],
							court=court,
							status='scheduled'
						)
			messages.success(request, f'Semi-Final round scheduled.')
		# Final
		elif next_round.order == 6:
			# 2 teams, single match
			from results.models import Score
			s_matches = Match.objects.filter(round__order=5)
			winners = [Score.objects.filter(match=m, winner__isnull=False).first().winner for m in s_matches if Score.objects.filter(match=m, winner__isnull=False).first()]
			if len(winners) == 2:
				with transaction.atomic():
					Match.objects.create(
						round=next_round,
						team1=winners[0],
						team2=winners[1],
						court=courts[0],
						status='scheduled'
					)
				messages.success(request, f'Final round scheduled.')
		else:
			messages.error(request, 'Unknown round logic or missing data.')
		return redirect('/admin/schedule')
		return redirect('/admin/schedule')

	# Determine selected round from GET param or default to first round
	show_round = request.GET.get('show_round')
	selected_round = None
	if show_round:
		try:
			selected_round = rounds.get(id=int(show_round))
		except Exception:
			selected_round = rounds.first()
	else:
		selected_round = rounds.first()

	# Now that selected_round and matches are defined, calculate has_matches_for_selected_round
	has_matches_for_selected_round = matches.filter(round=selected_round).exists() if selected_round else False

	# Calculate total matches per court for selected round
	court_match_counts = {}
	if selected_round:
		for court in courts:
			court_match_counts[court.id] = matches.filter(round=selected_round, court=court).count()

	context = {
		'rounds': rounds,
		'courts': courts,
		'groups': groups,
		'matches': matches,
		'next_round': next_round,
		'court_range': court_range,
		'show_round': show_round,
		'selected_round': selected_round,
		'has_matches_for_selected_round': has_matches_for_selected_round,
		'court_match_counts': court_match_counts,
		'locked_num_courts': locked_num_courts,
	}
	return render(request, 'schedule/admin_schedule.html', context)

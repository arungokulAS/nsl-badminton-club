

from django.shortcuts import render, redirect
from django.contrib import messages
from schedule.models import Round, Court
from matches.models import Match
from groups.models import Group
from teams.models import Team
from results.models import Score
from live.utils import build_qualifier_table
import os
import random

STANDARD_ROUND_NAMES = [
	'Group Stage',
	'Qualifier',
	'Pre-Quarter',
	'Quarter',
	'Semi Final',
	'Losers Final',
	'Final',
]

def admin_schedule(request):
	if not request.session.get('is_admin'):
		return redirect('/admin/login')

	def ensure_default_courts():
		if Court.objects.exists():
			return
		Court.objects.bulk_create([
			Court(name='Court 1'),
			Court(name='Court 2'),
			Court(name='Court 3'),
			Court(name='Court 4'),
			Court(name='Court 5'),
			Court(name='Court 6'),
			Court(name='Court 7'),
			Court(name='Court 8'),
		])

	def get_center_courts(courts_list):
		center = [court for court in courts_list if court.id in (3, 4)]
		if not center:
			center = [court for court in courts_list if court.name in ('Court 3', 'Court 4', '3', '4')]
		return center

	def schedule_qualifier_round(next_round, courts):
		from live.utils import build_group_tables
		group_tables = build_group_tables()
		group_rankings = {}
		for group_table in group_tables:
			group_name = group_table['group'].group_name
			if group_name.lower().startswith('group '):
				group_key = group_name.split(' ', 1)[1].strip().upper()
			else:
				group_key = group_name.strip().upper()
			group_rankings[group_key] = [row['team'] for row in group_table['rows'][:4]]
		if len(group_rankings) < 6:
			messages.error(request, 'Qualifier scheduling failed: missing group rankings.')
			return
		if not courts:
			messages.error(request, 'Qualifier scheduling failed: no courts available.')
			return
		pairings = [('A', 'F'), ('B', 'E'), ('C', 'D')]
		matches = []
		for g1, g2 in pairings:
			teams1 = group_rankings.get(g1, [])
			teams2 = group_rankings.get(g2, [])
			if len(teams1) < 4 or len(teams2) < 4:
				continue
			matches.append((teams1[0], teams2[3]))
			matches.append((teams1[1], teams2[2]))
			matches.append((teams1[2], teams2[1]))
			matches.append((teams1[3], teams2[0]))
		if len(matches) < 12:
			messages.error(request, 'Qualifier scheduling failed: not enough qualified teams per group.')
			return
		from django.db import transaction
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
		messages.success(request, 'Qualifier round scheduled.')

	rounds = Round.objects.filter(order__in=[1, 2, 3, 4, 5, 6, 7], name__in=STANDARD_ROUND_NAMES).order_by('order')
	ensure_default_courts()
	admin_password_env = os.environ.get('ADMIN_PASSWORD', 'admin123')
	# Ensure standard round flow (includes Losers Final)
	standard_rounds = [
		('Group Stage', 1),
		('Qualifier', 2),
		('Pre-Quarter', 3),
		('Quarter', 4),
		('Semi Final', 5),
		('Losers Final', 6),
		('Final', 7),
	]
	for name, order in standard_rounds:
		obj, created = Round.objects.get_or_create(name=name, defaults={'order': order})
		if not created and obj.order != order:
			obj.order = order
			obj.save(update_fields=['order'])
	rounds = Round.objects.filter(order__in=[1, 2, 3, 4, 5, 6, 7], name__in=STANDARD_ROUND_NAMES).order_by('order')
	# Lock court count after admin confirmation
	if 'unlock_courts' in request.POST and request.method == 'POST':
		if request.POST.get('admin_password') == admin_password_env:
			request.session['locked_num_courts'] = None
			messages.success(request, 'Court selection unlocked. You can now select a new number of courts.')
			return redirect('/admin/schedule')
		else:
			messages.error(request, 'Invalid admin password.')
			return redirect('/admin/schedule')

	if request.method == 'POST' and 'update_round_settings' in request.POST:
		admin_password = request.POST.get('admin_password')
		round_id = int(request.POST.get('round_id', 0))
		if admin_password != admin_password_env:
			messages.error(request, 'Invalid admin password.')
			return redirect('/admin/schedule')
		round_obj = Round.objects.filter(id=round_id).first()
		if not round_obj:
			messages.error(request, 'Invalid round.')
			return redirect('/admin/schedule')
		try:
			points_per_set = int(request.POST.get('points_per_set', round_obj.points_per_set))
			sets_per_match = int(request.POST.get('sets_per_match', round_obj.sets_per_match))
		except (TypeError, ValueError):
			messages.error(request, 'Invalid points or sets selection.')
			return redirect(f'/admin/schedule?show_round={round_obj.id}')
		if points_per_set not in (15, 21, 25, 30) or sets_per_match not in (1, 2, 3):
			messages.error(request, 'Points or sets selection is out of range.')
			return redirect(f'/admin/schedule?show_round={round_obj.id}')
		if not Match.objects.filter(round=round_obj).exists():
			messages.error(request, 'Schedule must be generated before locking round settings.')
			return redirect(f'/admin/schedule?show_round={round_obj.id}')
		round_obj.points_per_set = points_per_set
		round_obj.sets_per_match = sets_per_match
		if 'lock_round_settings' in request.POST:
			round_obj.settings_locked = True
			messages.success(request, 'Round settings locked.')
		elif 'unlock_round_settings' in request.POST:
			round_obj.settings_locked = False
			messages.success(request, 'Round settings unlocked.')
		round_obj.save(update_fields=['points_per_set', 'sets_per_match', 'settings_locked'])
		return redirect(f'/admin/schedule?show_round={round_obj.id}')

	# Finish round action
	if request.method == 'POST' and 'finish_round' in request.POST:
		admin_password = request.POST.get('admin_password')
		round_id = int(request.POST.get('round_id', 0))
		if admin_password != admin_password_env:
			messages.error(request, 'Invalid admin password.')
			return redirect('/admin/schedule')
		finish_round = Round.objects.filter(id=round_id).first()
		if not finish_round:
			messages.error(request, 'Invalid round.')
			return redirect('/admin/schedule')
		round_matches = Match.objects.filter(round=finish_round)
		if not round_matches.exists():
			messages.error(request, 'No matches found for this round.')
			return redirect('/admin/schedule')
		pending = round_matches.exclude(status='completed')
		if pending.exists():
			messages.error(request, 'All matches must be completed before finishing this round.')
			return redirect('/admin/schedule')
		scores_unlocked = Score.objects.filter(match__in=round_matches, locked=False)
		if scores_unlocked.exists():
			messages.error(request, 'All scores must be admin-confirmed before finishing this round.')
			return redirect('/admin/schedule')
		finish_round.is_finished = True
		finish_round.save(update_fields=['is_finished'])
		messages.success(request, f'{finish_round.name} finished. Next round unlocked.')
		next_round = Round.objects.filter(order=finish_round.order + 1).first()
		if next_round:
			from django.db import transaction
			locked_num_courts = request.session.get('locked_num_courts')
			courts = Court.objects.all().order_by('id')
			if locked_num_courts:
				courts = list(courts[:locked_num_courts])
			else:
				courts = list(courts)
			if finish_round.order == 1:
				if Match.objects.filter(round=next_round).exists():
					if Score.objects.filter(match__round=next_round, locked=True).exists():
						messages.error(request, 'Qualifier scheduling skipped: matches already have confirmed scores.')
						redirect_url = '/admin/schedule'
						if next_round:
							redirect_url = f'/admin/schedule?show_round={next_round.id}'
						return redirect(redirect_url)
					Match.objects.filter(round=next_round).delete()
				schedule_qualifier_round(next_round, courts)
			elif finish_round.order == 2:
				qualifier_scores = Score.objects.select_related('match', 'match__team1', 'match__team2').filter(
					match__round=finish_round,
					locked=True,
				)
				qualifier_stats = {}
				for score in qualifier_scores:
					team1 = score.match.team1
					team2 = score.match.team2
					for team in (team1, team2):
						if team and team.id not in qualifier_stats:
							qualifier_stats[team.id] = {
								'team': team,
								'wins': 0,
								'total_points': 0,
								'points_for': 0,
								'points_against': 0,
								'points_diff': 0,
							}
					if not team1 or not team2:
						continue
					qualifier_stats[team1.id]['points_for'] += score.team1_score
					qualifier_stats[team1.id]['points_against'] += score.team2_score
					qualifier_stats[team2.id]['points_for'] += score.team2_score
					qualifier_stats[team2.id]['points_against'] += score.team1_score
					if score.team1_score > score.team2_score:
						qualifier_stats[team1.id]['wins'] += 1
						qualifier_stats[team1.id]['total_points'] += 2
					elif score.team2_score > score.team1_score:
						qualifier_stats[team2.id]['wins'] += 1
						qualifier_stats[team2.id]['total_points'] += 2
				for row in qualifier_stats.values():
					row['points_diff'] = row['points_for'] - row['points_against']
				sorted_rows = sorted(
					qualifier_stats.values(),
					key=lambda row: (row['total_points'], row['points_diff'], row['points_for'], row['wins'], row['team'].team_name),
					reverse=True,
				)
				top_teams = [row['team'] for row in sorted_rows[:16]]
				if len(top_teams) < 16:
					fallback_teams = []
					qualifier_matches = Match.objects.select_related('team1', 'team2').filter(round=finish_round).order_by('id')
					for match in qualifier_matches:
						for team in (match.team1, match.team2):
							if team and team not in fallback_teams:
								fallback_teams.append(team)
					if len(fallback_teams) >= 16:
						top_teams = fallback_teams[:16]
				if len(top_teams) < 16:
					messages.error(request, 'Pre-Quarter scheduling failed: not enough qualified teams.')
				elif not courts:
					messages.error(request, 'Pre-Quarter scheduling failed: no courts available.')
				else:
					pairings = []
					for idx in range(8):
						pairings.append((top_teams[idx], top_teams[-(idx + 1)]))
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
					messages.success(request, 'Pre-Quarter round scheduled.')
			elif finish_round.order == 3:
				from live.utils import build_qualifier_table, build_prequarter_table
				qualifier_table = build_qualifier_table()
				prequarter_table, prequarter_qualified = build_prequarter_table(rounds, qualifier_table)
				ranked_winners = [row['team'] for row in prequarter_table if row.get('is_prequarter_qualified')]
				if len(ranked_winners) < 8:
					messages.error(request, 'Quarter scheduling failed: not enough ranked winners from Pre-Quarter.')
				elif not courts:
					messages.error(request, 'Quarter scheduling failed: no courts available.')
				else:
					pairings = []
					for idx in range(4):
						pairings.append((ranked_winners[idx], ranked_winners[-(idx + 1)]))
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
					messages.success(request, 'Quarter round scheduled.')
			elif finish_round.order == 4:
				quarter_scores = Score.objects.select_related('match', 'winner').filter(
					match__round=finish_round,
					locked=True,
				).order_by('match__id')
				winners = []
				for score in quarter_scores:
					if score.winner and score.winner not in winners:
						winners.append(score.winner)
				if len(winners) < 4:
					messages.error(request, 'Semi-Final scheduling failed: not enough winners from Quarter.')
				elif not courts:
					messages.error(request, 'Semi-Final scheduling failed: no courts available.')
				else:
					center_courts = get_center_courts(courts) or courts
					with transaction.atomic():
						for idx in range(0, len(winners), 2):
							if idx + 1 < len(winners):
								court = center_courts[(idx // 2) % len(center_courts)]
								Match.objects.create(
									round=next_round,
									team1=winners[idx],
									team2=winners[idx + 1],
									court=court,
									status='scheduled'
								)
					messages.success(request, 'Semi-Final round scheduled.')
			elif finish_round.order == 5:
				semi_matches = Match.objects.filter(round=finish_round)
				losers = []
				for match in semi_matches:
					score = Score.objects.filter(match=match, locked=True).first()
					if score and score.winner:
						loser = match.team1 if score.winner != match.team1 else match.team2
						losers.append(loser)
				if len(losers) == 2 and courts:
					with transaction.atomic():
						Match.objects.create(
							round=next_round,
							team1=losers[0],
							team2=losers[1],
							court=courts[0],
							status='scheduled'
						)
					messages.success(request, 'Losers Final scheduled.')
				elif not courts:
					messages.error(request, 'Losers Final scheduling failed: no courts available.')
				else:
					messages.error(request, 'Losers Final requires two confirmed semi-final losers.')
			elif finish_round.order == 6:
				semi_matches = Match.objects.filter(round__order=5)
				winners = []
				for match in semi_matches:
					score = Score.objects.filter(match=match, locked=True).first()
					if score and score.winner and score.winner not in winners:
						winners.append(score.winner)
				if len(winners) == 2 and courts:
					center_courts = get_center_courts(courts) or courts
					with transaction.atomic():
						Match.objects.create(
							round=next_round,
							team1=winners[0],
							team2=winners[1],
							court=center_courts[0],
							status='scheduled'
						)
					messages.success(request, 'Final round scheduled.')
				elif not courts:
					messages.error(request, 'Final scheduling failed: no courts available.')
				else:
					messages.error(request, 'Final requires two confirmed semi-final winners.')
			else:
				messages.error(request, 'Unknown round logic or missing data.')
		redirect_url = '/admin/schedule'
		if next_round:
			redirect_url = f'/admin/schedule?show_round={next_round.id}'
		return redirect(redirect_url)

	# Regenerate qualifier schedule using results
	if request.method == 'POST' and 'regen_qualifier' in request.POST:
		admin_password = request.POST.get('admin_password')
		if admin_password != admin_password_env:
			messages.error(request, 'Invalid admin password.')
			return redirect('/admin/schedule')
		qualifier_round = Round.objects.filter(name='Qualifier').first()
		if not qualifier_round:
			messages.error(request, 'Qualifier round not found.')
			return redirect('/admin/schedule')
		if Score.objects.filter(match__round=qualifier_round, locked=True).exists():
			messages.error(request, 'Cannot regenerate: qualifier matches already have confirmed scores.')
			return redirect(f'/admin/schedule?show_round={qualifier_round.id}')
		locked_num_courts = request.session.get('locked_num_courts')
		courts = Court.objects.all().order_by('id')
		if locked_num_courts:
			courts = list(courts[:locked_num_courts])
		else:
			courts = list(courts)
		Match.objects.filter(round=qualifier_round).delete()
		schedule_qualifier_round(qualifier_round, courts)
		return redirect(f'/admin/schedule?show_round={qualifier_round.id}')

	# Regenerate quarter schedule using pre-quarter rankings
	if request.method == 'POST' and 'regen_quarter' in request.POST:
		admin_password = request.POST.get('admin_password')
		if admin_password != admin_password_env:
			messages.error(request, 'Invalid admin password.')
			return redirect('/admin/schedule')
		quarter_round = Round.objects.filter(name__iexact='Quarter').first()
		if not quarter_round:
			messages.error(request, 'Quarter round not found.')
			return redirect('/admin/schedule')
		if Score.objects.filter(match__round=quarter_round, locked=True).exists():
			messages.error(request, 'Cannot regenerate: quarter matches already have confirmed scores.')
			return redirect(f'/admin/schedule?show_round={quarter_round.id}')
		locked_num_courts = request.session.get('locked_num_courts')
		courts = Court.objects.all().order_by('id')
		if locked_num_courts:
			courts = list(courts[:locked_num_courts])
		else:
			courts = list(courts)
		if not courts:
			messages.error(request, 'Quarter regeneration failed: no courts available.')
			return redirect(f'/admin/schedule?show_round={quarter_round.id}')
		from live.utils import build_qualifier_table, build_prequarter_table
		qualifier_table = build_qualifier_table()
		prequarter_table, prequarter_qualified = build_prequarter_table(rounds, qualifier_table)
		ranked_winners = [row['team'] for row in prequarter_table if row.get('is_prequarter_qualified')]
		if len(ranked_winners) < 8:
			messages.error(request, 'Quarter regeneration failed: not enough ranked winners from Pre-Quarter.')
			return redirect(f'/admin/schedule?show_round={quarter_round.id}')
		Match.objects.filter(round=quarter_round).delete()
		pairings = []
		for idx in range(4):
			pairings.append((ranked_winners[idx], ranked_winners[-(idx + 1)]))
		from django.db import transaction
		with transaction.atomic():
			for idx, (team1, team2) in enumerate(pairings):
				court = courts[idx % len(courts)]
				Match.objects.create(
					round=quarter_round,
					team1=team1,
					team2=team2,
					court=court,
					status='scheduled'
				)
		messages.success(request, 'Quarter round regenerated from pre-quarter rankings.')
		return redirect(f'/admin/schedule?show_round={quarter_round.id}')

	# AJAX: If this is an AJAX POST for locking courts, return only the referee dropdown HTML
	if request.method == 'POST' and request.headers.get('x-requested-with') == 'XMLHttpRequest' and 'lock_courts' in request.POST:
		# Only handle court locking, not schedule generation
		print(f"DEBUG: AJAX POST data: {request.POST}")
		admin_password = request.POST.get('admin_password')
		print(f"DEBUG: admin_password received: {admin_password}")
		locked_num_courts = int(request.POST.get('num_courts', 0))
		if admin_password == admin_password_env and locked_num_courts:
			request.session['locked_num_courts'] = locked_num_courts
			print(f"DEBUG: locked_num_courts set to {locked_num_courts}")
			request.session.save()  # Force session save
		else:
			print("DEBUG: Password incorrect or num_courts missing")
		from django.template.loader import render_to_string
		from django.http import JsonResponse
		courts = Court.objects.all().order_by('id')[:locked_num_courts] if locked_num_courts else []
		groups = Group.objects.all().order_by('group_name')
		groups_locked = groups.exists() and groups.first().is_locked
		total_courts = Court.objects.count()
		max_courts = min(8, total_courts) if total_courts else 8
		court_range = range(1, max_courts + 1)
		next_round = rounds.filter(is_finished=False).order_by('order').first() if rounds.exists() else None
		# Render referee dropdown + court lock panel HTML
		dropdown_html = render_to_string('partials/referee_dropdown_nav.html', {'locked_courts': courts})
		lock_panel_html = render_to_string(
			'schedule/partials/court_lock_panel.html',
			{
				'groups_locked': groups_locked,
				'locked_num_courts': locked_num_courts,
				'court_range': court_range,
				'next_round': next_round,
			},
			request=request,
		)
		return JsonResponse({'dropdown_html': dropdown_html, 'lock_panel_html': lock_panel_html})

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
	groups_locked = groups.exists() and groups.first().is_locked
	matches = Match.objects.select_related('round', 'court', 'team1', 'team2').filter(round__order__in=[1, 2, 3, 4, 5, 6, 7], round__name__in=STANDARD_ROUND_NAMES).order_by('round__order', 'court__id')
	# Always allow selection from 1 to 8 (or total number of courts if less than 8)
	total_courts = Court.objects.count()
	max_courts = min(8, total_courts) if total_courts else 8
	court_range = range(1, max_courts + 1)


	from django.db import transaction
	next_round = rounds.filter(is_finished=False).order_by('order').first() if rounds.exists() else None

	if request.method == 'POST' and 'generate_schedule' in request.POST and next_round:
		if not groups_locked:
			message = 'Groups must be locked before scheduling courts.'
			messages.error(request, message)
			if request.headers.get('x-requested-with') == 'XMLHttpRequest':
				from django.http import JsonResponse
				return JsonResponse({'error': message}, status=400)
			return redirect('/admin/schedule')
		requested_round_id = int(request.POST.get('round', 0))
		num_courts = len(courts)
		if not courts:
			message = 'No courts defined.'
			messages.error(request, message)
			if request.headers.get('x-requested-with') == 'XMLHttpRequest':
				from django.http import JsonResponse
				return JsonResponse({'error': message}, status=400)
			return redirect('/admin/schedule')
		if int(request.POST.get('num_courts', 0)) > Court.objects.count():
			message = 'Invalid number of courts.'
			messages.error(request, message)
			if request.headers.get('x-requested-with') == 'XMLHttpRequest':
				from django.http import JsonResponse
				return JsonResponse({'error': message}, status=400)
			return redirect('/admin/schedule')
		# Enforce previous round completion for non-group rounds
		if next_round.order > 1:
			prev_round = None
			if next_round.name.lower().startswith('losers') or next_round.name.lower() == 'final':
				prev_round = rounds.filter(name__iexact='Semi Final').first()
			else:
				prev_round = rounds.filter(order=next_round.order - 1).first()
			if prev_round and not prev_round.is_finished:
				message = 'Previous round must be finished before scheduling this round.'
				messages.error(request, message)
				if request.headers.get('x-requested-with') == 'XMLHttpRequest':
					from django.http import JsonResponse
					return JsonResponse({'error': message}, status=400)
				return redirect('/admin/schedule')
		if requested_round_id != next_round.id:
			message = 'You can only schedule the next unfinished round.'
			messages.error(request, message)
			if request.headers.get('x-requested-with') == 'XMLHttpRequest':
				from django.http import JsonResponse
				return JsonResponse({'error': message}, status=400)
			return redirect('/admin/schedule')
		# Allow regeneration if round has not started
		existing_matches = Match.objects.filter(round_id=requested_round_id)
		if existing_matches.exists():
			if existing_matches.exclude(status='scheduled').exists():
				message = 'Round already started. Cannot regenerate schedule.'
				messages.error(request, message)
				if request.headers.get('x-requested-with') == 'XMLHttpRequest':
					from django.http import JsonResponse
					return JsonResponse({'error': message}, status=400)
				return redirect('/admin/schedule')
			existing_matches.delete()
		round_id = requested_round_id
		# Group Stage
		if next_round.order == 1 and groups.exists():
			if groups.count() != 6:
				message = 'Group Stage requires exactly 6 groups.'
				messages.error(request, message)
				if request.headers.get('x-requested-with') == 'XMLHttpRequest':
					from django.http import JsonResponse
					return JsonResponse({'error': message}, status=400)
				return redirect('/admin/schedule')
			for group in groups:
				if group.teams.count() != 6:
					message = f'Group {group.group_name} must have 6 teams.'
					messages.error(request, message)
					if request.headers.get('x-requested-with') == 'XMLHttpRequest':
						from django.http import JsonResponse
						return JsonResponse({'error': message}, status=400)
					return redirect('/admin/schedule')
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
				# Map 'A', 'B', ... to Group objects
				group_objs = {}
				for g in groups:
					code = g.group_name.strip().upper()
					if code.startswith('GROUP '):
						code = code.replace('GROUP ', '')
					group_objs[code] = g
				group_codes = list(group_objs.keys())
				# Build matches for each group
				group_matches = {}
				for g in group_codes:
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
				from collections import deque
				master_schedule = []
				team_last_slots = {}
				court_queues = [deque(slots) for slots in court_slots]
				time_slot = 0
				max_cycles = sum(len(q) for q in court_queues) * 20 + 200
				cycles = 0
				while any(court_queues) and cycles < max_cycles:
					progress = False
					for cidx, court in enumerate(courts):
						if cidx >= len(court_queues) or not court_queues[cidx]:
							continue
						queue = court_queues[cidx]
						attempts = 0
						scheduled = False
						while attempts < len(queue):
							group, team1, team2 = queue[0]
							recent1 = team_last_slots.get(team1.id, deque(maxlen=2))
							recent2 = team_last_slots.get(team2.id, deque(maxlen=2))
							conflict1 = len(recent1) == 2 and recent1[0] == time_slot - 2 and recent1[1] == time_slot - 1
							conflict2 = len(recent2) == 2 and recent2[0] == time_slot - 2 and recent2[1] == time_slot - 1
							if conflict1 or conflict2:
								queue.rotate(-1)
								attempts += 1
								continue
							queue.popleft()
							master_schedule.append((court, group, team1, team2))
							if team1.id not in team_last_slots:
								team_last_slots[team1.id] = deque(maxlen=2)
							if team2.id not in team_last_slots:
								team_last_slots[team2.id] = deque(maxlen=2)
							team_last_slots[team1.id].append(time_slot)
							team_last_slots[team2.id].append(time_slot)
							progress = True
							scheduled = True
							break
						if scheduled:
							continue
					cycles += 1
					time_slot += 1
					if not progress:
						cycles += 1
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
			schedule_qualifier_round(next_round, courts)
		# Pre-Quarter
		elif next_round.order == 3:
			# 12 qualifier winners + 4 best losers
			qualifier_matches = Match.objects.filter(round__order=2)
			winners = [Score.objects.filter(match=m, winner__isnull=False, locked=True).first().winner for m in qualifier_matches if Score.objects.filter(match=m, winner__isnull=False, locked=True).first()]
			losers = [m.team1 if Score.objects.filter(match=m, locked=True).first().winner != m.team1 else m.team2 for m in qualifier_matches if Score.objects.filter(match=m, locked=True).first()]
			# Rank losers
			def score_total(team):
				score = Score.objects.filter(match__team1=team, locked=True).first() or Score.objects.filter(match__team2=team, locked=True).first()
				if not score:
					return 0
				return score.team1_score + score.team2_score
			best_losers = sorted(losers, key=score_total, reverse=True)[:4]
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
			preq_matches = Match.objects.filter(round__order=3)
			winners = [Score.objects.filter(match=m, winner__isnull=False, locked=True).first().winner for m in preq_matches if Score.objects.filter(match=m, winner__isnull=False, locked=True).first()]
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
			q_matches = Match.objects.filter(round__order=4)
			winners = [Score.objects.filter(match=m, winner__isnull=False, locked=True).first().winner for m in q_matches if Score.objects.filter(match=m, winner__isnull=False, locked=True).first()]
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
		# Losers Final (3rd place)
		elif next_round.name.lower().startswith('losers'):
			semi_matches = Match.objects.filter(round__order=5)
			losers = []
			for m in semi_matches:
				score = Score.objects.filter(match=m, locked=True).first()
				if score and score.winner:
					loser = m.team1 if score.winner != m.team1 else m.team2
					losers.append(loser)
				if len(losers) == 2:
					break
			if len(losers) == 2:
				with transaction.atomic():
					Match.objects.create(
						round=next_round,
						team1=losers[0],
						team2=losers[1],
						court=courts[0],
						status='scheduled'
					)
				messages.success(request, f'Losers Final scheduled.')
			else:
				messages.error(request, 'Losers Final requires two confirmed semi-final losers.')
		# Final
		elif next_round.name.lower() == 'final' or next_round.order == 7:
			# 2 teams, single match
			s_matches = Match.objects.filter(round__order=5)
			winners = [Score.objects.filter(match=m, winner__isnull=False, locked=True).first().winner for m in s_matches if Score.objects.filter(match=m, winner__isnull=False, locked=True).first()]
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
		if request.headers.get('x-requested-with') == 'XMLHttpRequest':
			from django.template.loader import render_to_string
			from django.http import JsonResponse
			rounds = Round.objects.all().order_by('order')
			locked_num_courts = request.session.get('locked_num_courts')
			courts = Court.objects.all().order_by('id')
			if locked_num_courts:
				courts = list(courts[:locked_num_courts])
			else:
				courts = list(courts)
			groups = Group.objects.all().order_by('group_name')
			matches = Match.objects.select_related('round', 'court', 'team1', 'team2').all().order_by('round__order', 'court__id')
			show_round = request.GET.get('show_round')
			current_round = rounds.filter(is_finished=False).first() if rounds.exists() else None
			selected_round = None
			if show_round:
				try:
					selected_round = rounds.get(id=int(show_round))
				except Exception:
					selected_round = current_round or rounds.first()
			else:
				selected_round = current_round or rounds.first()
			show_round = selected_round.id if selected_round else None
			has_matches_for_selected_round = matches.filter(round=selected_round).exists() if selected_round else False
			selected_round_match_count = matches.filter(round=selected_round).count() if selected_round else 0
			court_match_counts = {}
			court_match_groups = []
			if selected_round:
				display_courts = courts
				if selected_round.order in (5, 7):
					center_courts = get_center_courts(courts)
					center_with_matches = [court for court in center_courts if matches.filter(round=selected_round, court=court).exists()]
					if center_with_matches:
						display_courts = center_with_matches
					else:
						display_courts = [court for court in courts if matches.filter(round=selected_round, court=court).exists()]
				elif selected_round.order == 6:
					display_courts = [court for court in courts if matches.filter(round=selected_round, court=court).exists()]
				for court in display_courts:
					court_matches = matches.filter(round=selected_round, court=court)
					court_match_counts[court.id] = court_matches.count()
					court_match_groups.append({
						'court': court,
						'matches': list(court_matches),
						'count': court_matches.count(),
					})
			context = {
				'rounds': rounds,
				'courts': courts,
				'groups': groups,
				'matches': matches,
				'show_round': show_round,
				'selected_round': selected_round,
				'has_matches_for_selected_round': has_matches_for_selected_round,
				'court_match_counts': court_match_counts,
				'selected_round_match_count': selected_round_match_count,
				'court_match_groups': court_match_groups,
			}
			matchtables_html = render_to_string('schedule/partials/match_tables.html', context, request=request)
			return JsonResponse({'matchtables_html': matchtables_html})
		return redirect('/admin/schedule')

	# Determine selected round from GET param or default to current round
	show_round = request.GET.get('show_round')
	current_round = rounds.filter(is_finished=False).first() if rounds.exists() else None
	selected_round = None
	if show_round:
		try:
			selected_round = rounds.get(id=int(show_round))
		except Exception:
			selected_round = current_round or rounds.first()
	else:
		selected_round = current_round or rounds.first()
	show_round = selected_round.id if selected_round else None

	# Now that selected_round and matches are defined, calculate has_matches_for_selected_round
	has_matches_for_selected_round = matches.filter(round=selected_round).exists() if selected_round else False
	selected_round_match_count = matches.filter(round=selected_round).count() if selected_round else 0

	# Calculate total matches per court for selected round
	court_match_counts = {}
	court_match_groups = []
	if selected_round:
		display_courts = courts
		if selected_round.order in (5, 7):
			center_courts = get_center_courts(courts)
			center_with_matches = [court for court in center_courts if matches.filter(round=selected_round, court=court).exists()]
			if center_with_matches:
				display_courts = center_with_matches
			else:
				display_courts = [court for court in courts if matches.filter(round=selected_round, court=court).exists()]
		elif selected_round.order == 6:
			display_courts = [court for court in courts if matches.filter(round=selected_round, court=court).exists()]
		for court in display_courts:
			court_matches = matches.filter(round=selected_round, court=court)
			court_match_counts[court.id] = court_matches.count()
			court_match_groups.append({
				'court': court,
				'matches': list(court_matches),
				'count': court_matches.count(),
			})

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
		'selected_round_match_count': selected_round_match_count,
		'court_match_groups': court_match_groups,
		'locked_num_courts': locked_num_courts,
		'groups_locked': groups_locked,
	}
	return render(request, 'schedule/admin_schedule.html', context)

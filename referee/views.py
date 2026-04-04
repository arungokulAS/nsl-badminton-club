from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponseForbidden, JsonResponse
from schedule.models import Court, Round
from groups.models import Group
from matches.models import Match
from results.models import Score
from teams.models import Team
from .tokens import validate_referee_token
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.cache import never_cache
from django.template.loader import render_to_string
from django.utils import timezone
from .tokens import generate_referee_token
from schedule.models import Court, Round
from django.urls import reverse
import logging
from django.db import transaction, IntegrityError

logger = logging.getLogger("referee")

STANDARD_ROUND_NAMES = [
	'Group Stage',
	'Qualifier',
	'Pre-Quarter',
	'Quarter',
	'Semi Final',
	'Losers Final',
	'Final',
]

def admin_generate_token(request):
	if not request.session.get('is_admin'):
		return redirect('/admin/login')
	token_url = None
	groups = Group.objects.all().order_by('group_name')
	groups_locked = groups.exists() and groups.first().is_locked
	locked_num_courts = request.session.get('locked_num_courts')
	if groups_locked and locked_num_courts:
		courts = Court.objects.all()[: int(locked_num_courts)]
	else:
		courts = Court.objects.none()
	rounds = Round.objects.filter(order__in=[1, 2, 3, 4, 5, 6, 7], name__in=STANDARD_ROUND_NAMES).order_by('order')
	has_unlocked_rounds = rounds.filter(settings_locked=False).exists()
	has_locked_rounds = rounds.filter(settings_locked=True).exists()
	if request.method == 'POST':
		court_id = request.POST.get('court_id')
		round_id = request.POST.get('round_id')
		if not groups_locked or not locked_num_courts:
			return HttpResponseForbidden('Courts are not locked for referee access.')
		round_obj = Round.objects.filter(id=round_id).first()
		if not round_obj or not round_obj.settings_locked:
			return HttpResponseForbidden('Round settings must be locked before generating referee links.')
		token = generate_referee_token(court_id, round_id)
		base_url = request.build_absolute_uri('/')[:-1]
		token_url = f"{base_url}{reverse('referee_court_page', args=[court_id])}?token={token}"
	return render(request, 'referee/admin_tokens.html', {
		'courts': courts,
		'rounds': rounds,
		'token_url': token_url,
		'groups_locked': groups_locked,
		'locked_num_courts': locked_num_courts,
		'has_unlocked_rounds': has_unlocked_rounds,
		'has_locked_rounds': has_locked_rounds,
	})
def referee_court_page(request, court_id):
	token = request.GET.get('token')
	if not token:
		return render(request, 'referee/court/invalid_token.html', {
			'message': 'Missing referee token.',
		}, status=403)
	token_data = validate_referee_token(token)
	if not token_data or int(token_data['court_id']) != int(court_id):
		return render(request, 'referee/court/invalid_token.html', {
			'message': 'Invalid or expired referee token.',
		}, status=403)
	teams = Team.objects.all().order_by('id')
	if not teams.exists() or not teams.first().is_locked:
		return render(request, 'referee/court/invalid_token.html', {
			'message': 'Referee access is disabled until teams are locked.',
		}, status=403)

	court = get_object_or_404(Court, id=court_id)
	round_id = token_data['round_id']
	round_obj = get_object_or_404(Round, id=round_id)
	if not round_obj.settings_locked:
		return render(request, 'referee/court/invalid_token.html', {
			'message': 'Round settings are not locked yet.',
		}, status=403)
	active_round = Round.objects.filter(order__in=[1, 2, 3, 4, 5, 6, 7], name__in=STANDARD_ROUND_NAMES).filter(is_finished=False).order_by('order').first()
	if active_round and round_obj.id != active_round.id:
		return render(request, 'referee/court/invalid_token.html', {
			'message': 'Referee access is limited to the current active round.',
		}, status=403)
	if round_obj.is_finished:
		return render(request, 'referee/court/invalid_token.html', {
			'message': 'Referee token expired for this round.',
		}, status=403)

	# Show matches for this court/round that are still being scored by referee
	matches = Match.objects.filter(
		court=court,
		round=round_obj,
		status='scheduled',
	).order_by('id')
	score_map = {score.match_id: score for score in Score.objects.filter(match__in=matches)}

	def _next_set_number(score_obj, sets_per_match):
		if not score_obj or not score_obj.set1_submitted:
			return 1
		if sets_per_match >= 2 and not score_obj.set2_submitted:
			return 2
		if sets_per_match >= 3 and not score_obj.set3_submitted:
			return 3
		return None

	def _set_field_names(set_number):
		return (
			f'team1_set{set_number}',
			f'team2_set{set_number}',
			f'set{set_number}_submitted',
		)

	if request.method == 'POST':
		try:
			match_id = request.POST.get('match_id')
			submit_set_raw = request.POST.get('submit_set')
			submit_winner_raw = request.POST.get('submit_winner')
			if not match_id:
				return HttpResponseForbidden('Match is required.')
			try:
				match_id_int = int(match_id)
			except (TypeError, ValueError):
				return HttpResponseForbidden('Invalid match id.')
			match = get_object_or_404(Match, id=match_id_int, court=court, round=round_obj)
			sets_per_match = max(1, min(round_obj.sets_per_match, 3))
			if not match.team1 or not match.team2:
				return HttpResponseForbidden('Match teams are missing.')
			if match.status != 'scheduled':
				return HttpResponseForbidden('Match is not available for scoring.')

			if submit_winner_raw:
				winner_raw = request.POST.get('winner')
				try:
					submit_winner = int(winner_raw)
				except (TypeError, ValueError):
					return HttpResponseForbidden('Invalid winner submission.')
				if sets_per_match != 3:
					return HttpResponseForbidden('Winner submission is available for 3-set rounds only.')
				if submit_winner not in (1, 2):
					return HttpResponseForbidden('Invalid winner selection.')
				with transaction.atomic():
					score = Score.objects.filter(match=match).first()
					if not score:
						return HttpResponseForbidden('Please submit set scores first.')
					if score.locked:
						return HttpResponseForbidden('Score is already admin-confirmed.')
					all_submitted = score.set1_submitted and score.set2_submitted and score.set3_submitted
					if not all_submitted:
						return HttpResponseForbidden('All sets must be submitted before winner selection.')

					team1_sets = 0
					team2_sets = 0
					for team1_set_score, team2_set_score in [
						(score.team1_set1, score.team2_set1),
						(score.team1_set2, score.team2_set2),
						(score.team1_set3, score.team2_set3),
					]:
						if team1_set_score is None or team2_set_score is None:
							return HttpResponseForbidden('Missing set scores.')
						if team1_set_score == team2_set_score:
							return HttpResponseForbidden('Set score cannot be tied.')
						if team1_set_score > team2_set_score:
							team1_sets += 1
						else:
							team2_sets += 1
					if team1_sets == team2_sets:
						return HttpResponseForbidden('Overall winner could not be determined.')
					expected_winner = 1 if team1_sets > team2_sets else 2
					if submit_winner != expected_winner:
						return HttpResponseForbidden('Winner selection does not match set results.')

					score.winner = match.team1 if submit_winner == 1 else match.team2
					score.team1_score = (score.team1_set1 or 0) + (score.team1_set2 or 0) + (score.team1_set3 or 0)
					score.team2_score = (score.team2_set1 or 0) + (score.team2_set2 or 0) + (score.team2_set3 or 0)
					score.save(update_fields=['winner', 'team1_score', 'team2_score'])
					match.status = 'awaiting_admin_confirmation'
					match.save(update_fields=['status'])
				logger.info(
					"Referee winner submission: match=%s court=%s round=%s winner=%s",
					match.id,
					court.id,
					round_obj.id,
					submit_winner,
				)
				return redirect(request.path + f'?token={token}')

			try:
				submit_set = int(submit_set_raw)
			except (TypeError, ValueError):
				return HttpResponseForbidden('Invalid set submission.')
			if submit_set < 1 or submit_set > sets_per_match:
				return HttpResponseForbidden('Set number is out of range.')
			team1_value_raw = request.POST.get(f'team1_set{submit_set}')
			team2_value_raw = request.POST.get(f'team2_set{submit_set}')
			set_winner = request.POST.get(f'set_winner{submit_set}')
			try:
				team1_value = int(team1_value_raw)
				team2_value = int(team2_value_raw)
			except (TypeError, ValueError):
				return HttpResponseForbidden('Invalid score values.')
			if team1_value == team2_value:
				return HttpResponseForbidden('Set score cannot be tied.')
			if sets_per_match == 1:
				if set_winner not in ('1', '2'):
					return HttpResponseForbidden('Set winner selection is required.')
				expected_winner = '1' if team1_value > team2_value else '2'
				if set_winner != expected_winner:
					return HttpResponseForbidden('Set winner does not match entered score.')
			with transaction.atomic():
				score, _ = Score.objects.get_or_create(
					match=match,
					defaults={
						'team1_score': 0,
						'team2_score': 0,
						'locked': False,
					},
				)
				if score.locked:
					return HttpResponseForbidden('Score is already admin-confirmed.')
				next_set = _next_set_number(score, sets_per_match)
				if next_set is None:
					return HttpResponseForbidden('All sets are already submitted.')
				if submit_set != next_set:
					return HttpResponseForbidden(f'Please submit Set {next_set} next.')

				team1_field, team2_field, submitted_field = _set_field_names(submit_set)
				setattr(score, team1_field, team1_value)
				setattr(score, team2_field, team2_value)
				setattr(score, submitted_field, True)

				score.team1_score = (score.team1_set1 or 0) + (score.team1_set2 or 0) + (score.team1_set3 or 0)
				score.team2_score = (score.team2_set1 or 0) + (score.team2_set2 or 0) + (score.team2_set3 or 0)

				all_submitted = (
					score.set1_submitted and
					(sets_per_match < 2 or score.set2_submitted) and
					(sets_per_match < 3 or score.set3_submitted)
				)
				if all_submitted:
					if sets_per_match == 1:
						score.winner = match.team1 if set_winner == '1' else match.team2
						match.status = 'awaiting_admin_confirmation'
						match.save(update_fields=['status'])
					elif sets_per_match == 2:
						team1_sets = 0
						team2_sets = 0
						for team1_set_score, team2_set_score in [
							(score.team1_set1, score.team2_set1),
							(score.team1_set2, score.team2_set2),
						]:
							if team1_set_score is None or team2_set_score is None:
								return HttpResponseForbidden('Missing set scores.')
							if team1_set_score == team2_set_score:
								return HttpResponseForbidden('Set score cannot be tied.')
							if team1_set_score > team2_set_score:
								team1_sets += 1
							else:
								team2_sets += 1
						if team1_sets == team2_sets:
							return HttpResponseForbidden('Overall winner could not be determined.')
						score.winner = match.team1 if team1_sets > team2_sets else match.team2
						match.status = 'awaiting_admin_confirmation'
						match.save(update_fields=['status'])
				score.save()
			logger.info(
				"Referee set submission: match=%s court=%s round=%s set=%s team1=%s team2=%s score1=%s score2=%s",
				match.id,
				court.id,
				round_obj.id,
				submit_set,
				match.team1_id,
				match.team2_id,
				team1_value,
				team2_value,
			)
			return redirect(request.path + f'?token={token}')
		except Exception:
			logger.exception("Referee submission failed")
			return HttpResponseForbidden('Unable to submit score. Please retry.')

	for match in matches:
		score = score_map.get(match.id)
		sets_per_match = max(1, min(round_obj.sets_per_match, 3))
		match.partial_score = score
		match.next_set_number = _next_set_number(score, sets_per_match)
		match.all_sets_submitted = bool(
			score and
			score.set1_submitted and
			(sets_per_match < 2 or score.set2_submitted) and
			(sets_per_match < 3 or score.set3_submitted)
		)

	context = {
		'court': court,
		'round': round_obj,
		'matches': matches,
		'set_numbers': list(range(1, max(1, min(round_obj.sets_per_match, 3)) + 1)),
	}
	return render(request, 'referee/court/court_referee.html', context)

from django.shortcuts import render, redirect
from matches.models import Match
from results.models import Score
from django.contrib import messages
from django.db import transaction

@never_cache
def admin_live_manage(request):
	if not request.session.get('is_admin'):
		return redirect('/admin/login')

	matches = Match.objects.select_related('team1', 'team2', 'court', 'round').filter(round__order__in=[1, 2, 3, 4, 5, 6, 7], round__name__in=STANDARD_ROUND_NAMES).order_by('court__id', 'id')
	current_round = Round.objects.filter(order__in=[1, 2, 3, 4, 5, 6, 7], name__in=STANDARD_ROUND_NAMES).filter(is_finished=False).order_by('order').first()
	if not current_round:
		current_round = Round.objects.filter(order__in=[1, 2, 3, 4, 5, 6, 7], name__in=STANDARD_ROUND_NAMES).order_by('-order').first()
	if current_round:
		matches = matches.filter(round=current_round)
	matches = matches.filter(status__in=['scheduled', 'awaiting_admin_confirmation', 'completed'])
	scores = {s.match_id: s for s in Score.objects.filter(match__in=matches)}

	def _is_all_sets_submitted(score, sets_per_match):
		return (
			score.set1_submitted and
			(sets_per_match < 2 or score.set2_submitted) and
			(sets_per_match < 3 or score.set3_submitted)
		)

	def _determine_winner_from_sets(match, score, sets_per_match):
		team1_sets = 0
		team2_sets = 0
		set_pairs = [
			(score.team1_set1, score.team2_set1),
			(score.team1_set2, score.team2_set2),
			(score.team1_set3, score.team2_set3),
		]
		for index in range(sets_per_match):
			team1_set_score, team2_set_score = set_pairs[index]
			if team1_set_score is None or team2_set_score is None:
				return None
			if team1_set_score == team2_set_score:
				return None
			if team1_set_score > team2_set_score:
				team1_sets += 1
			else:
				team2_sets += 1
		if team1_sets == team2_sets:
			return None
		return match.team1 if team1_sets > team2_sets else match.team2

	def _attach_match_flags(match_queryset, score_map):
		for listed_match in match_queryset:
			score_obj = score_map.get(listed_match.id)
			sets_per_match = max(1, min(listed_match.round.sets_per_match, 3))
			listed_match.referee_ready = bool(score_obj and _is_all_sets_submitted(score_obj, sets_per_match))
			listed_match.score_locked = bool(score_obj and score_obj.locked)

	_attach_match_flags(matches, scores)

	if request.method == 'POST':
		try:
			match_id_raw = request.POST.get('match_id')
			try:
				match_id = int(match_id_raw)
			except (TypeError, ValueError):
				messages.error(request, 'Invalid match id.')
				return redirect('/admin/live-manage')
			action = request.POST.get('action')

			if action not in ('save_set', 'edit_score'):
				messages.error(request, 'Invalid action.')
				return redirect('/admin/live-manage')

			with transaction.atomic():
				match = Match.objects.filter(id=match_id).select_related('team1', 'team2', 'round').first()
				if not match:
					messages.error(request, 'Match not found.')
					return redirect('/admin/live-manage')
				sets_per_match = max(1, min(match.round.sets_per_match, 3))
				score = Score.objects.filter(match=match).first()
				if not score:
					messages.error(request, 'Waiting for referee score submission.')
					return redirect('/admin/live-manage')

				if action == 'edit_score':
					if score.locked:
						score.locked = False
						score.save(update_fields=['locked'])
						match.status = 'awaiting_admin_confirmation'
						match.save(update_fields=['status'])
						messages.success(request, 'Score unlocked for editing.')
					else:
						messages.info(request, 'Score is already editable.')
					return redirect('/admin/live-manage')

				if score.locked:
					messages.info(request, 'Score is already confirmed. Use Edit to modify.')
					return redirect('/admin/live-manage')
				if not _is_all_sets_submitted(score, sets_per_match):
					messages.error(request, 'All set scores must be submitted by referee before saving.')
					return redirect('/admin/live-manage')

				set_number_raw = request.POST.get('set_number')
				try:
					set_number = int(set_number_raw)
				except (TypeError, ValueError):
					messages.error(request, 'Invalid set number.')
					return redirect('/admin/live-manage')
				if set_number < 1 or set_number > sets_per_match:
					messages.error(request, 'Set number is out of range.')
					return redirect('/admin/live-manage')

				set_submitted = (
					score.set1_submitted if set_number == 1
					else score.set2_submitted if set_number == 2
					else score.set3_submitted
				)
				if not set_submitted:
					messages.error(request, 'Selected set is not yet submitted by referee.')
					return redirect('/admin/live-manage')

				team1_value_raw = request.POST.get('team1_value')
				team2_value_raw = request.POST.get('team2_value')
				try:
					team1_value = int(team1_value_raw)
					team2_value = int(team2_value_raw)
				except (TypeError, ValueError):
					messages.error(request, 'Invalid score values.')
					return redirect('/admin/live-manage')
				if team1_value == team2_value:
					messages.error(request, 'Score cannot be tied.')
					return redirect('/admin/live-manage')

				if set_number == 1:
					score.team1_set1 = team1_value
					score.team2_set1 = team2_value
				elif set_number == 2:
					score.team1_set2 = team1_value
					score.team2_set2 = team2_value
				else:
					score.team1_set3 = team1_value
					score.team2_set3 = team2_value

				score.team1_score = (score.team1_set1 or 0) + (score.team1_set2 or 0) + (score.team1_set3 or 0)
				score.team2_score = (score.team2_set1 or 0) + (score.team2_set2 or 0) + (score.team2_set3 or 0)

				winner = _determine_winner_from_sets(match, score, sets_per_match)
				if not winner:
					messages.error(request, 'Unable to determine winner from submitted set scores.')
					return redirect('/admin/live-manage')
				score.winner = winner
				score.locked = True
				score.save(update_fields=[
					'team1_set1', 'team2_set1',
					'team1_set2', 'team2_set2',
					'team1_set3', 'team2_set3',
					'team1_score', 'team2_score',
					'winner', 'locked',
				])
				match.status = 'completed'
				match.save(update_fields=['status'])
				messages.success(request, 'Score saved and confirmed.')
				return redirect('/admin/live-manage')
		except Exception:
			logger.exception('Admin live-manage submit failed')
			messages.error(request, 'Unable to save score. Please retry.')
			return redirect('/admin/live-manage')

	context = {
		'matches': matches,
		'scores': scores,
		'current_round': current_round,
		'show_group_column': bool(current_round and current_round.name == 'Group Stage'),
	}
	return render(request, 'referee/admin_live_manage.html', context)


@never_cache
def admin_live_manage_fragment(request):
	if not request.session.get('is_admin'):
		return JsonResponse({'html': ''}, status=403)

	matches = Match.objects.select_related('team1', 'team2', 'court', 'round').filter(
		round__order__in=[1, 2, 3, 4, 5, 6, 7],
		round__name__in=STANDARD_ROUND_NAMES,
	).order_by('court__id', 'id')
	current_round = Round.objects.filter(
		order__in=[1, 2, 3, 4, 5, 6, 7],
		name__in=STANDARD_ROUND_NAMES,
	).filter(is_finished=False).order_by('order').first()
	if not current_round:
		current_round = Round.objects.filter(
			order__in=[1, 2, 3, 4, 5, 6, 7],
			name__in=STANDARD_ROUND_NAMES,
		).order_by('-order').first()
	if current_round:
		matches = matches.filter(round=current_round)
	# Show only pending/confirmed updates from referee
	matches = matches.filter(status__in=['scheduled', 'awaiting_admin_confirmation', 'completed'])
	scores = {s.match_id: s for s in Score.objects.filter(match__in=matches)}

	def _is_all_sets_submitted(score, sets_per_match):
		return (
			score.set1_submitted and
			(sets_per_match < 2 or score.set2_submitted) and
			(sets_per_match < 3 or score.set3_submitted)
		)

	for listed_match in matches:
		score_obj = scores.get(listed_match.id)
		sets_per_match = max(1, min(listed_match.round.sets_per_match, 3))
		listed_match.referee_ready = bool(score_obj and _is_all_sets_submitted(score_obj, sets_per_match))
		listed_match.score_locked = bool(score_obj and score_obj.locked)

	context = {
		'matches': matches,
		'scores': scores,
		'current_round': current_round,
		'show_group_column': bool(current_round and current_round.name == 'Group Stage'),
	}
	html = render_to_string('referee/partials/admin_live_manage_table.html', context, request=request)
	return JsonResponse({'html': html})

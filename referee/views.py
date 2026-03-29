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

	# Only show matches for this court, this round, and not already submitted
	matches = Match.objects.filter(
		court=court,
		round=round_obj,
		score__isnull=True,
	).order_by('id')

	if request.method == 'POST':
		try:
			match_id = request.POST.get('match_id')
			winner = request.POST.get('winner')
			if not match_id:
				return HttpResponseForbidden('Match is required.')
			try:
				match_id_int = int(match_id)
			except (TypeError, ValueError):
				return HttpResponseForbidden('Invalid match id.')
			match = get_object_or_404(Match, id=match_id_int, court=court, round=round_obj)
			sets_per_match = max(1, min(round_obj.sets_per_match, 3))
			set_values = []
			set_winners = []
			for set_index in range(1, sets_per_match + 1):
				team1_value = request.POST.get(f'team1_set{set_index}')
				team2_value = request.POST.get(f'team2_set{set_index}')
				set_winner = request.POST.get(f'set_winner{set_index}')
				try:
					team1_value = int(team1_value)
					team2_value = int(team2_value)
				except (TypeError, ValueError):
					return HttpResponseForbidden('Invalid score values.')
				if set_winner not in ('1', '2'):
					return HttpResponseForbidden('Set winner selection is required.')
				set_values.append((team1_value, team2_value))
				set_winners.append(set_winner)
			score1 = sum(value[0] for value in set_values)
			score2 = sum(value[1] for value in set_values)
			team1_sets = sum(1 for set_winner in set_winners if set_winner == '1')
			team2_sets = sum(1 for set_winner in set_winners if set_winner == '2')
			if team1_sets == team2_sets:
				return HttpResponseForbidden('Overall winner could not be determined.')
			winner = '1' if team1_sets > team2_sets else '2'
			if not match.team1 or not match.team2:
				return HttpResponseForbidden('Match teams are missing.')
			if match.status != 'scheduled':
				return HttpResponseForbidden('Match is not available for scoring.')
			# Save score as awaiting admin confirmation (handle concurrent submissions safely)
			try:
				with transaction.atomic():
					score, created = Score.objects.get_or_create(
						match=match,
						defaults={
							'team1_score': score1,
							'team2_score': score2,
							'team1_set1': set_values[0][0] if len(set_values) > 0 else None,
							'team2_set1': set_values[0][1] if len(set_values) > 0 else None,
							'team1_set2': set_values[1][0] if len(set_values) > 1 else None,
							'team2_set2': set_values[1][1] if len(set_values) > 1 else None,
							'team1_set3': set_values[2][0] if len(set_values) > 2 else None,
							'team2_set3': set_values[2][1] if len(set_values) > 2 else None,
							'winner': match.team1 if winner == '1' else match.team2,
							'locked': False,
						},
					)
					if not created:
						return HttpResponseForbidden('Score already submitted for this match.')
					match.status = 'awaiting_admin_confirmation'
					match.save(update_fields=['status'])
			except IntegrityError:
				return HttpResponseForbidden('Score already submitted for this match.')
			logger.info(
				"Referee submission: match=%s court=%s round=%s team1=%s team2=%s score1=%s score2=%s winner=%s",
				match.id,
				court.id,
				round_obj.id,
				match.team1_id,
				match.team2_id,
				score1,
				score2,
				match.team1_id if winner == '1' else match.team2_id,
			)
			return redirect(request.path + f'?token={token}')
		except Exception:
			logger.exception("Referee submission failed")
			return HttpResponseForbidden('Unable to submit score. Please retry.')

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
	scores = {s.match_id: s for s in Score.objects.all()}

	if request.method == 'POST':
		try:
			match_id_raw = request.POST.get('match_id')
			try:
				match_id = int(match_id_raw)
			except (TypeError, ValueError):
				messages.error(request, 'Invalid match id.')
				return redirect('/admin/live-manage')
			if 'edit_score' in request.POST:
				with transaction.atomic():
					score = Score.objects.filter(match_id=match_id).first()
					if not score:
						messages.error(request, 'Score not found for this match.')
					elif score.locked:
						score.locked = False
						score.save(update_fields=['locked'])
						messages.success(request, 'Score unlocked for editing.')
					else:
						messages.info(request, 'Score is already editable.')
				return redirect('/admin/live-manage')

			winner = request.POST.get('winner')
			with transaction.atomic():
				match = Match.objects.filter(id=match_id).first()
				if not match:
					messages.error(request, 'Match not found.')
					return redirect('/admin/live-manage')
				sets_per_match = max(1, min(match.round.sets_per_match, 3))
				set_values = []
				for set_index in range(1, sets_per_match + 1):
					team1_value = request.POST.get(f'team1_set{set_index}')
					team2_value = request.POST.get(f'team2_set{set_index}')
					try:
						team1_value = int(team1_value)
						team2_value = int(team2_value)
					except (TypeError, ValueError):
						messages.error(request, 'Invalid score values.')
						return redirect('/admin/live-manage')
					set_values.append((team1_value, team2_value))
				team1_score = sum(value[0] for value in set_values)
				team2_score = sum(value[1] for value in set_values)
				if winner not in ('1', '2'):
					messages.error(request, 'Winner selection is required.')
					return redirect('/admin/live-manage')
				winner_obj = match.team1 if winner == '1' else match.team2
				score, created = Score.objects.get_or_create(match=match)
				if score.locked:
					messages.error(request, 'Score is locked for this match.')
				else:
					score.team1_score = team1_score
					score.team2_score = team2_score
					score.team1_set1 = set_values[0][0] if len(set_values) > 0 else None
					score.team2_set1 = set_values[0][1] if len(set_values) > 0 else None
					score.team1_set2 = set_values[1][0] if len(set_values) > 1 else None
					score.team2_set2 = set_values[1][1] if len(set_values) > 1 else None
					score.team1_set3 = set_values[2][0] if len(set_values) > 2 else None
					score.team2_set3 = set_values[2][1] if len(set_values) > 2 else None
					score.winner = winner_obj
					score.locked = True
					score.save()
					match.status = 'completed'
					match.save()
					messages.success(request, 'Score confirmed.')
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
	scores = {s.match_id: s for s in Score.objects.all()}

	context = {
		'matches': matches,
		'scores': scores,
		'current_round': current_round,
		'show_group_column': bool(current_round and current_round.name == 'Group Stage'),
	}
	html = render_to_string('referee/partials/admin_live_manage_table.html', context, request=request)
	return JsonResponse({'html': html})

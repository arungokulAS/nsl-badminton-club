from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponseForbidden
from schedule.models import Court, Round
from groups.models import Group
from matches.models import Match
from results.models import Score
from teams.models import Team
from .tokens import validate_referee_token
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from .tokens import generate_referee_token
from schedule.models import Court, Round
from django.urls import reverse
import logging

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
	if request.method == 'POST':
		court_id = request.POST.get('court_id')
		round_id = request.POST.get('round_id')
		if not groups_locked or not locked_num_courts:
			return HttpResponseForbidden('Courts are not locked for referee access.')
		token = generate_referee_token(court_id, round_id)
		base_url = request.build_absolute_uri('/')[:-1]
		token_url = f"{base_url}{reverse('referee_court_page', args=[court_id])}?token={token}"
	return render(request, 'referee/admin_tokens.html', {
		'courts': courts,
		'rounds': rounds,
		'token_url': token_url,
		'groups_locked': groups_locked,
		'locked_num_courts': locked_num_courts,
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
	active_round = Round.objects.filter(order__in=[1, 2, 3, 4, 5, 6, 7], name__in=STANDARD_ROUND_NAMES).filter(is_finished=False).order_by('order').first()
	if active_round and round_obj.id != active_round.id:
		return render(request, 'referee/court/invalid_token.html', {
			'message': 'Referee access is limited to the current active round.',
		}, status=403)
	if round_obj.is_finished:
		return render(request, 'referee/court/invalid_token.html', {
			'message': 'Referee token expired for this round.',
		}, status=403)

	# Only show matches for this court, this round, not completed, and not already submitted
	matches = Match.objects.filter(
		court=court,
		round=round_obj,
		status='scheduled',
	).exclude(score__isnull=False).order_by('id')

	if request.method == 'POST':
		match_id = request.POST.get('match_id')
		score1 = request.POST.get('score1')
		score2 = request.POST.get('score2')
		winner = request.POST.get('winner')
		match = get_object_or_404(Match, id=match_id, court=court, round=round_obj)
		try:
			score1 = int(score1)
			score2 = int(score2)
		except (TypeError, ValueError):
			return HttpResponseForbidden('Invalid score values.')
		if match.status != 'scheduled':
			return HttpResponseForbidden('Match is not available for scoring.')
		# Prevent double submission
		if Score.objects.filter(match=match).exists():
			return HttpResponseForbidden('Score already submitted for this match.')
		# Save score as awaiting admin confirmation
		Score.objects.create(
			match=match,
			team1_score=score1,
			team2_score=score2,
			winner=match.team1 if winner == '1' else match.team2,
			locked=False
		)
		match.status = 'awaiting_admin_confirmation'
		match.save()
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

	context = {
		'court': court,
		'round': round_obj,
		'matches': matches,
	}
	return render(request, 'referee/court/court_referee.html', context)

from django.shortcuts import render, redirect
from matches.models import Match
from results.models import Score
from django.contrib import messages
from django.db import transaction

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
		match_id = int(request.POST.get('match_id'))
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

		team1_score = int(request.POST.get('team1_score'))
		team2_score = int(request.POST.get('team2_score'))
		with transaction.atomic():
			match = Match.objects.get(id=match_id)
			winner = match.team1 if team1_score > team2_score else match.team2 if team2_score > team1_score else None
			score, created = Score.objects.get_or_create(match=match)
			if score.locked:
				messages.error(request, 'Score is locked for this match.')
			else:
				score.team1_score = team1_score
				score.team2_score = team2_score
				score.winner = winner
				score.locked = True
				score.save()
				match.status = 'completed'
				match.save()
				messages.success(request, 'Score confirmed.')
		return redirect('/admin/live-manage')

	context = {
		'matches': matches,
		'scores': scores,
		'current_round': current_round,
		'show_group_column': bool(current_round and current_round.name == 'Group Stage'),
	}
	return render(request, 'referee/admin_live_manage.html', context)

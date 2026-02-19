from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponseForbidden
from schedule.models import Court, Round
from matches.models import Match
from results.models import Score
from .tokens import validate_referee_token
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from .tokens import generate_referee_token
from schedule.models import Court, Round
from django.urls import reverse
from django.contrib.admin.views.decorators import staff_member_required

@staff_member_required
def admin_generate_token(request):
	token_url = None
	courts = Court.objects.all()
	rounds = Round.objects.all()
	if request.method == 'POST':
		court_id = request.POST.get('court_id')
		round_id = request.POST.get('round_id')
		token = generate_referee_token(court_id, round_id)
		base_url = request.build_absolute_uri('/')[:-1]
		token_url = f"{base_url}{reverse('referee_court_page', args=[court_id])}?token={token}"
	return render(request, 'referee/admin_tokens.html', {'courts': courts, 'rounds': rounds, 'token_url': token_url})
def referee_court_page(request, court_id):
	token = request.GET.get('token')
	if not token:
		return HttpResponseForbidden('Missing referee token.')
	token_data = validate_referee_token(token)
	if not token_data or int(token_data['court_id']) != int(court_id):
		return HttpResponseForbidden('Invalid or expired referee token.')

	court = get_object_or_404(Court, id=court_id)
	round_id = token_data['round_id']
	round_obj = get_object_or_404(Round, id=round_id)

	# Only show matches for this court, this round, not completed
	matches = Match.objects.filter(court=court, round=round_obj, status='scheduled')

	if request.method == 'POST':
		match_id = request.POST.get('match_id')
		score1 = request.POST.get('score1')
		score2 = request.POST.get('score2')
		winner = request.POST.get('winner')
		match = get_object_or_404(Match, id=match_id, court=court, round=round_obj)
		# Prevent double submission
		if Score.objects.filter(match=match).exists():
			return HttpResponseForbidden('Score already submitted for this match.')
		# Save score as awaiting admin confirmation
		Score.objects.create(
			match=match,
			team1_score=score1,
			team2_score=score2,
			winner=match.team1 if winner == '1' else match.team2,
			locked=True
		)
		match.status = 'awaiting_admin_confirmation'
		match.save()
		return redirect(request.path + f'?token={token}')

	# Mark matches as submitted if score exists
	match_list = []
	for m in matches:
		m.submitted = Score.objects.filter(match=m).exists()
		match_list.append(m)

	context = {
		'court': court,
		'round': round_obj,
		'matches': match_list,
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

	matches = Match.objects.select_related('team1', 'team2', 'court', 'round').order_by('round__order', 'court__id')
	scores = {s.match_id: s for s in Score.objects.all()}

	if request.method == 'POST':
		match_id = int(request.POST.get('match_id'))
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
				score.save()
				match.status = 'completed'
				match.save()
				messages.success(request, 'Score updated.')
		return redirect('/admin/live-manage')

	context = {
		'matches': matches,
		'scores': scores,
	}
	return render(request, 'referee/admin_live_manage.html', context)

from django.shortcuts import render, redirect
from django.contrib import messages
from schedule.models import Round
from matches.models import Match
from results.models import Score
from django.db import transaction

def admin_finish_round(request):
    if not request.session.get('is_admin'):
        return redirect('/admin/login')

    rounds = Round.objects.all().order_by('order')
    current_round = rounds.filter(is_finished=False).order_by('order').first() if rounds.exists() else None
    finished = False

    if request.method == 'POST' and current_round:
        # Lock all scores for this round and mark round as finished
        matches = Match.objects.filter(round=current_round)
        with transaction.atomic():
            for match in matches:
                score = Score.objects.filter(match=match).first()
                if score:
                    score.locked = True
                    score.save()
                match.status = 'locked'
                match.save()
            current_round.is_finished = True
            current_round.save()
            finished = True
            messages.success(request, f"{current_round.name} locked and finished.")
        return redirect('/admin/finish-round')

    context = {
        'rounds': rounds,
        'current_round': current_round,
        'finished': finished,
    }
    return render(request, 'schedule/admin_finish_round.html', context)

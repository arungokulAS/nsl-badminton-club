from django.shortcuts import redirect, render

from groups.models import Group
from matches.models import Match
from schedule.models import Round
from core.models import TournamentRegistration
from teams.models import Team

STANDARD_ROUND_NAMES = [
    'Group Stage',
    'Qualifier',
    'Pre-Quarter',
    'Quarter',
    'Semi Final',
    'Losers Final',
    'Final',
]

def public_referee(request):
    return render(request, 'core/public_referee.html')

def public_contact(request):
    return render(request, 'core/public_contact.html')


def public_register(request):
    if request.method == 'POST':
        team_name = request.POST.get('team_name', '').strip()
        player1_name = request.POST.get('player1_name', '').strip()
        player2_name = request.POST.get('player2_name', '').strip()
        contact_phone = request.POST.get('contact_phone', '').strip()
        contact_email = request.POST.get('contact_email', '').strip()
        city = request.POST.get('city', '').strip()
        notes = request.POST.get('notes', '').strip()

        if team_name and player1_name and player2_name and contact_phone:
            TournamentRegistration.objects.create(
                team_name=team_name,
                player1_name=player1_name,
                player2_name=player2_name,
                contact_phone=contact_phone,
                contact_email=contact_email,
                city=city,
                notes=notes,
            )
            return redirect('/register?success=1')

        return render(
            request,
            'core/public_register.html',
            {
                'error': 'Please fill all required fields.',
                'form_data': {
                    'team_name': team_name,
                    'player1_name': player1_name,
                    'player2_name': player2_name,
                    'contact_phone': contact_phone,
                    'contact_email': contact_email,
                    'city': city,
                    'notes': notes,
                },
                'success': request.GET.get('success') == '1',
            },
        )

    return render(
        request,
        'core/public_register.html',
        {
            'success': request.GET.get('success') == '1',
            'form_data': {},
        },
    )

def print_menu(request):
    teams = Team.objects.all().order_by('team_name')
    groups = Group.objects.prefetch_related('teams').all().order_by('group_name')
    rounds = Round.objects.filter(order__in=[1, 2, 3, 4, 5, 6, 7], name__in=STANDARD_ROUND_NAMES).order_by('order')
    matches = Match.objects.select_related('round', 'court', 'team1', 'team2').filter(
        round__order__in=[1, 2, 3, 4, 5, 6, 7],
        round__name__in=STANDARD_ROUND_NAMES,
    ).order_by('round__order', 'court__name', 'id')
    context = {
        'teams': teams,
        'groups': groups,
        'rounds': rounds,
        'matches': matches,
    }
    return render(request, 'core/print_menu.html', context)

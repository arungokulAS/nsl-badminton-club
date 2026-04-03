from django.shortcuts import redirect, render
from django.conf import settings
from django.core.mail import send_mail

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
    valid_categories = {'A', 'B', 'C', 'D', 'E'}
    valid_relations = {'Father', 'Brother', 'Sister', 'Mother', 'Wife', 'Friend'}
    valid_media_consents = {'agree', 'do_not_agree'}

    if request.method == 'POST':
        player1_first_name = request.POST.get('player1_first_name', '').strip()
        player1_last_name = request.POST.get('player1_last_name', '').strip()
        player1_category = request.POST.get('player1_category', '').strip()
        player1_contact_number = request.POST.get('player1_contact_number', '').strip()
        player1_email = request.POST.get('player1_email', '').strip()
        player1_city = request.POST.get('player1_city', '').strip()

        player2_first_name = request.POST.get('player2_first_name', '').strip()
        player2_last_name = request.POST.get('player2_last_name', '').strip()
        player2_category = request.POST.get('player2_category', '').strip()
        player2_contact_number = request.POST.get('player2_contact_number', '').strip()
        player2_email = request.POST.get('player2_email', '').strip()
        player2_city = request.POST.get('player2_city', '').strip()

        emergency_contact_name = request.POST.get('emergency_contact_name', '').strip()
        emergency_contact_number = request.POST.get('emergency_contact_number', '').strip()
        emergency_contact_relation = request.POST.get('emergency_contact_relation', '').strip()
        declaration_confirmed = request.POST.get('declaration_confirmed') == 'on'
        media_consent = request.POST.get('media_consent', '').strip()

        required_fields = [
            player1_first_name,
            player1_last_name,
            player1_category,
            player1_contact_number,
            player1_email,
            player1_city,
            player2_first_name,
            player2_last_name,
            player2_category,
            player2_contact_number,
            player2_email,
            player2_city,
            emergency_contact_name,
            emergency_contact_number,
            emergency_contact_relation,
        ]

        if all(required_fields) and player1_category in valid_categories and player2_category in valid_categories and emergency_contact_relation in valid_relations and declaration_confirmed and media_consent in valid_media_consents:
            team_name = f"{player1_first_name} {player1_last_name} / {player2_first_name} {player2_last_name}"
            TournamentRegistration.objects.create(
                team_name=team_name,
                player1_first_name=player1_first_name,
                player1_last_name=player1_last_name,
                player1_category=player1_category,
                player1_contact_number=player1_contact_number,
                player1_email=player1_email,
                player1_city=player1_city,
                player2_first_name=player2_first_name,
                player2_last_name=player2_last_name,
                player2_category=player2_category,
                player2_contact_number=player2_contact_number,
                player2_email=player2_email,
                player2_city=player2_city,
                emergency_contact_name=emergency_contact_name,
                emergency_contact_number=emergency_contact_number,
                emergency_contact_relation=emergency_contact_relation,
                declaration_confirmed=declaration_confirmed,
                media_consent=media_consent,
            )

            recipients = [player1_email]
            if player2_email and player2_email.lower() != player1_email.lower():
                recipients.append(player2_email)

            subject = '🎉 You’re Almost In! NSL Badminton Tournament Registration'
            message = (
                "Hey Team! 🏸\n\n"
                "Thanks for signing up for the NSL Badminton Tournament 2025! "
                "Your registration details are safely with us.\n\n"
                "Just a quick heads-up: slots are limited, and your spot is official only after the registration fee is received. "
                "First to pay = first on the official teams list! ⏱️\n\n"
                "Payment Info:\n\n"
                "• Account Name: MR A J JOY\n\n"
                "• Account Number: 89857653\n\n"
                "• Sort Code: 09-01-28\n\n"
                f"• Reference: {team_name}\n\n"
                "Once your payment hits our account, we’ll send you a final confirmation via WhatsApp and email.\n\n"
                "Get ready to smash it on the court! 💪\n\n"
                "“Bring the game to life!”\n\n"
                "Cheers,\n\n"
                "NSL Badminton Tournament Team"
            )

            try:
                send_mail(
                    subject=subject,
                    message=message,
                    from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'netsmashersliverpool@gmail.com'),
                    recipient_list=recipients,
                    fail_silently=True,
                )
            except Exception:
                pass

            return redirect('/register?success=1')

        return render(
            request,
            'core/public_register.html',
            {
                'error': 'Please complete all required fields, declaration, and consent options.',
                'form_data': {
                    'player1_first_name': player1_first_name,
                    'player1_last_name': player1_last_name,
                    'player1_category': player1_category,
                    'player1_contact_number': player1_contact_number,
                    'player1_email': player1_email,
                    'player1_city': player1_city,
                    'player2_first_name': player2_first_name,
                    'player2_last_name': player2_last_name,
                    'player2_category': player2_category,
                    'player2_contact_number': player2_contact_number,
                    'player2_email': player2_email,
                    'player2_city': player2_city,
                    'emergency_contact_name': emergency_contact_name,
                    'emergency_contact_number': emergency_contact_number,
                    'emergency_contact_relation': emergency_contact_relation,
                    'declaration_confirmed': declaration_confirmed,
                    'media_consent': media_consent,
                },
                'success': request.GET.get('success') == '1',
                'categories': sorted(valid_categories),
                'relations': ['Father', 'Brother', 'Sister', 'Mother', 'Wife', 'Friend'],
                'media_consents': [
                    ('agree', 'I agree'),
                    ('do_not_agree', 'I do not agree'),
                ],
            },
        )

    return render(
        request,
        'core/public_register.html',
        {
            'success': request.GET.get('success') == '1',
            'form_data': {},
            'categories': ['A', 'B', 'C', 'D', 'E'],
            'relations': ['Father', 'Brother', 'Sister', 'Mother', 'Wife', 'Friend'],
            'media_consents': [
                ('agree', 'I agree'),
                ('do_not_agree', 'I do not agree'),
            ],
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

from django.shortcuts import redirect, render
from django.conf import settings
from django.core.mail import get_connection
from django.core.mail import send_mail
import threading
import logging
import json
import time
from urllib import error as urllib_error
from urllib import request as urllib_request

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

logger = logging.getLogger(__name__)


def _send_registration_confirmation_email_async(recipients, team_name):
    if not recipients:
        return
    if not getattr(settings, 'REGISTRATION_CONFIRMATION_EMAIL_ENABLED', True):
        return
    resend_api_key = getattr(settings, 'RESEND_API_KEY', '').strip()
    email_backend = getattr(settings, 'EMAIL_BACKEND', '')
    email_password = getattr(settings, 'EMAIL_HOST_PASSWORD', '')
    max_attempts = max(1, int(getattr(settings, 'REGISTRATION_CONFIRMATION_EMAIL_MAX_ATTEMPTS', 8)))
    retry_delay_seconds = max(0.0, float(getattr(settings, 'REGISTRATION_CONFIRMATION_EMAIL_RETRY_DELAY_SECONDS', 0.0)))
    if not resend_api_key and 'smtp.EmailBackend' in email_backend and not email_password:
        logger.warning(
            'Registration confirmation email skipped because no transport credentials are configured (SMTP password/API key). recipients=%s',
            recipients,
        )
        return

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

    def _send():
        connection = None
        if not resend_api_key:
            connection = get_connection(
                fail_silently=False,
                timeout=getattr(settings, 'EMAIL_TIMEOUT', 8),
            )

        for recipient in recipients:
            delivered = False

            for attempt in range(1, max_attempts + 1):
                try:
                    if resend_api_key:
                        payload = {
                            'from': getattr(settings, 'RESEND_FROM_EMAIL', '') or 'onboarding@resend.dev',
                            'to': [recipient],
                            'subject': subject,
                            'text': message,
                        }
                        req = urllib_request.Request(
                            url='https://api.resend.com/emails',
                            data=json.dumps(payload).encode('utf-8'),
                            headers={
                                'Authorization': f'Bearer {resend_api_key}',
                                'Content-Type': 'application/json',
                            },
                            method='POST',
                        )
                        timeout = getattr(settings, 'EMAIL_TIMEOUT', 8)
                        with urllib_request.urlopen(req, timeout=timeout) as response:
                            if response.status < 200 or response.status >= 300:
                                body = response.read().decode('utf-8', errors='ignore')
                                raise RuntimeError(f'Resend API returned {response.status}: {body}')
                    else:
                        send_mail(
                            subject=subject,
                            message=message,
                            from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'netsmashersliverpool@gmail.com'),
                            recipient_list=[recipient],
                            fail_silently=False,
                            connection=connection,
                        )

                    delivered = True
                    break
                except urllib_error.HTTPError:
                    logger.exception(
                        'Registration confirmation email failed via Resend HTTP API for recipient=%s team=%s attempt=%s/%s',
                        recipient,
                        team_name,
                        attempt,
                        max_attempts,
                    )
                except urllib_error.URLError:
                    logger.exception(
                        'Registration confirmation email failed via Resend network error for recipient=%s team=%s attempt=%s/%s',
                        recipient,
                        team_name,
                        attempt,
                        max_attempts,
                    )
                except Exception:
                    logger.exception(
                        'Registration confirmation email failed for recipient=%s team=%s attempt=%s/%s',
                        recipient,
                        team_name,
                        attempt,
                        max_attempts,
                    )

                if attempt < max_attempts and retry_delay_seconds > 0:
                    time.sleep(retry_delay_seconds)

            if not delivered:
                logger.warning(
                    'Registration confirmation email permanently failed after %s attempts for recipient=%s team=%s',
                    max_attempts,
                    recipient,
                    team_name,
                )

    if not getattr(settings, 'REGISTRATION_CONFIRMATION_EMAIL_ASYNC', True):
        _send()
        return

    thread = threading.Thread(target=_send, daemon=True)
    thread.start()

def public_referee(request):
    return render(request, 'core/public_referee.html')

def public_contact(request):
    return render(request, 'core/public_contact.html')


def public_register(request):
    valid_categories = {'A', 'B', 'C', 'D', 'E'}
    valid_relations = {'Father', 'Brother', 'Sister', 'Mother', 'Wife', 'Friend'}

    def _render_register_form(*, form_data=None, error=None, success=False, already_submitted=False):
        return render(
            request,
            'core/public_register.html',
            {
                'error': error,
                'form_data': form_data or {},
                'success': success,
                'already_submitted': already_submitted,
                'categories': sorted(valid_categories),
                'relations': ['Father', 'Brother', 'Sister', 'Mother', 'Wife', 'Friend'],
            },
        )

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
        declaration_info_true = request.POST.get('declaration_info_true') == 'on'
        declaration_rules_agreed = request.POST.get('declaration_rules_agreed') == 'on'
        media_consent = request.POST.get('media_consent', '').strip()

        declaration_confirmed = declaration_info_true and declaration_rules_agreed
        valid_media_consents = {'agree', 'do_not_agree'}

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

        if all(required_fields) and player1_category in valid_categories and player2_category in valid_categories and emergency_contact_relation in valid_relations and declaration_info_true and declaration_rules_agreed and media_consent in valid_media_consents:
            team_name = f"{player1_first_name} {player1_last_name} / {player2_first_name} {player2_last_name}"

            existing_registration = TournamentRegistration.objects.filter(
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
            ).exists()

            if existing_registration:
                return _render_register_form(
                    form_data={
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
                        'declaration_info_true': declaration_info_true,
                        'declaration_rules_agreed': declaration_rules_agreed,
                        'media_consent': media_consent,
                    },
                    already_submitted=True,
                )

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

            _send_registration_confirmation_email_async(recipients, team_name)

            return redirect('/register?success=1')

        return _render_register_form(
            error='Please complete all required fields, declaration, and consent options.',
            form_data={
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
                'declaration_info_true': declaration_info_true,
                'declaration_rules_agreed': declaration_rules_agreed,
                'media_consent': media_consent,
            },
        )

    return _render_register_form(success=request.GET.get('success') == '1')

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

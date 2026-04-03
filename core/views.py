from django.shortcuts import redirect, render

from core.models import TournamentRegistration


def admin_registered_teams(request):
	if not request.session.get('is_admin'):
		return redirect('/admin/login')

	if request.method == 'POST' and 'edit_registration' in request.POST:
		registration_id = request.POST.get('registration_id')
		if registration_id:
			registration = TournamentRegistration.objects.filter(id=registration_id).first()
			if registration:
				registration.player1_first_name = request.POST.get('player1_first_name', '').strip()
				registration.player1_last_name = request.POST.get('player1_last_name', '').strip()
				registration.player1_category = request.POST.get('player1_category', '').strip()
				registration.player1_contact_number = request.POST.get('player1_contact_number', '').strip()
				registration.player1_email = request.POST.get('player1_email', '').strip()
				registration.player1_city = request.POST.get('player1_city', '').strip()

				registration.player2_first_name = request.POST.get('player2_first_name', '').strip()
				registration.player2_last_name = request.POST.get('player2_last_name', '').strip()
				registration.player2_category = request.POST.get('player2_category', '').strip()
				registration.player2_contact_number = request.POST.get('player2_contact_number', '').strip()
				registration.player2_email = request.POST.get('player2_email', '').strip()
				registration.player2_city = request.POST.get('player2_city', '').strip()

				registration.emergency_contact_name = request.POST.get('emergency_contact_name', '').strip()
				registration.emergency_contact_number = request.POST.get('emergency_contact_number', '').strip()
				registration.emergency_contact_relation = request.POST.get('emergency_contact_relation', '').strip()
				registration.declaration_confirmed = request.POST.get('declaration_confirmed') == 'on'
				registration.media_consent = request.POST.get('media_consent', '').strip()
				registration.team_name = f"{registration.player1_first_name} {registration.player1_last_name} / {registration.player2_first_name} {registration.player2_last_name}"
				registration.save()

		return redirect('/admin/registered-teams')

	registrations = TournamentRegistration.objects.all().order_by('-created_at')
	context = {
		'registrations': registrations,
		'categories': ['A', 'B', 'C', 'D', 'E'],
		'relations': ['Father', 'Brother', 'Sister', 'Mother', 'Wife', 'Friend'],
		'media_consents': [('agree', 'I agree'), ('do_not_agree', 'I do not agree')],
	}
	return render(request, 'core/admin_registered_teams.html', context)

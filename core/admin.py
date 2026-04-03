from django.contrib import admin
from core.models import TournamentRegistration


@admin.register(TournamentRegistration)
class TournamentRegistrationAdmin(admin.ModelAdmin):
	list_display = (
		'team_name',
		'player1_first_name',
		'player2_first_name',
		'emergency_contact_number',
		'created_at',
	)
	search_fields = (
		'team_name',
		'player1_first_name',
		'player1_last_name',
		'player2_first_name',
		'player2_last_name',
		'player1_contact_number',
		'player2_contact_number',
		'emergency_contact_number',
	)

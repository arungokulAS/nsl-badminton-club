from django.contrib import admin
from core.models import TournamentRegistration


@admin.register(TournamentRegistration)
class TournamentRegistrationAdmin(admin.ModelAdmin):
	list_display = ('team_name', 'player1_name', 'player2_name', 'contact_phone', 'created_at')
	search_fields = ('team_name', 'player1_name', 'player2_name', 'contact_phone', 'contact_email')

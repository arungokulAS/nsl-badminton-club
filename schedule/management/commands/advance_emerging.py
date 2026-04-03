from django.core.management.base import BaseCommand

from schedule.emerging import advance_emerging_rounds


class Command(BaseCommand):
    help = 'Advance Emerging event rounds based on locked winners.'

    def handle(self, *args, **options):
        result = advance_emerging_rounds()
        if result.get('advanced'):
            self.stdout.write(self.style.SUCCESS(result['message']))
        else:
            self.stdout.write(self.style.WARNING(result['message']))

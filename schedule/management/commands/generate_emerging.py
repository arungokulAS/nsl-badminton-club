from django.core.management.base import BaseCommand

from schedule.emerging import generate_emerging_bracket


class Command(BaseCommand):
    help = 'Generate Emerging Quarter from bottom 8 Group Stage teams by lowest diff.'

    def add_arguments(self, parser):
        parser.add_argument('--force', action='store_true', help='Regenerate Emerging rounds and matches.')

    def handle(self, *args, **options):
        result = generate_emerging_bracket(force=options['force'])
        if result.get('created'):
            self.stdout.write(self.style.SUCCESS(result['message']))
        else:
            self.stdout.write(self.style.WARNING(result['message']))

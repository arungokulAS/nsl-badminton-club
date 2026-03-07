from pathlib import Path

from django.core.management.base import BaseCommand
from django.core.management import call_command


class Command(BaseCommand):
	help = "Import JSON fixture into the database (idempotent-ish)."

	def add_arguments(self, parser):
		parser.add_argument(
			"--input",
			default="fixtures/initial_data.json",
			help="Input fixture path (default: fixtures/initial_data.json)",
		)

	def handle(self, *args, **options):
		input_path = Path(options["input"])
		if not input_path.exists():
			self.stdout.write(self.style.WARNING(f"No fixture found at {input_path}; skipping import."))
			return

		call_command("loaddata", str(input_path))
		self.stdout.write(self.style.SUCCESS(f"Imported data from {input_path}"))

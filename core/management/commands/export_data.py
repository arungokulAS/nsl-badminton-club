from pathlib import Path

from django.core.management.base import BaseCommand
from django.core.management import call_command


class Command(BaseCommand):
	help = "Export local database data to a JSON fixture."

	def add_arguments(self, parser):
		parser.add_argument(
			"--output",
			default="fixtures/initial_data.json",
			help="Output fixture path (default: fixtures/initial_data.json)",
		)

	def handle(self, *args, **options):
		output_path = Path(options["output"])
		output_path.parent.mkdir(parents=True, exist_ok=True)

		exclude = [
			"contenttypes",
			"auth.permission",
		]

		with output_path.open("w", encoding="utf-8") as handle:
			call_command(
				"dumpdata",
				"--natural-foreign",
				"--natural-primary",
				"--indent",
				"2",
				"--exclude",
				*exclude,
				stdout=handle,
			)

		self.stdout.write(self.style.SUCCESS(f"Exported data to {output_path}"))

from django.core.management.base import BaseCommand
from reconcile.importer import DataImporter


class Command(BaseCommand):
    help = "Import reconciliation source CSV files (locations.csv, system_a.csv, system_b.csv) into SQLite."

    def add_arguments(self, parser):
        parser.add_argument(
            '--data-dir',
            type=str,
            default=None,
            help='Directory containing the CSV files'
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("Starting DealerOS CSV Data Import..."))
        importer = DataImporter(data_dir=options.get('data_dir'))
        summary = importer.import_all()

        self.stdout.write(self.style.SUCCESS("=== IMPORT SUMMARY REPORT ==="))
        self.stdout.write(f"Locations read:          {summary.locations_read}")
        self.stdout.write(f"Locations saved:         {summary.locations_saved}")
        self.stdout.write(f"System A rows read:      {summary.system_a_read}")
        self.stdout.write(f"System A rows saved:     {summary.system_a_saved}")
        self.stdout.write(f"System B rows read:      {summary.system_b_read}")
        self.stdout.write(f"System B rows saved:     {summary.system_b_saved}")
        self.stdout.write(f"Blank values:            {summary.blank_values}")
        self.stdout.write(f"Invalid amounts:         {summary.invalid_amounts}")
        self.stdout.write(f"Invalid dates:           {summary.invalid_dates}")
        self.stdout.write(f"Normalized references:   {summary.normalized_refs}")
        self.stdout.write(f"Unrecognized references: {summary.unrecognized_refs}")
        self.stdout.write(f"Unknown locations:       {summary.unknown_locations}")
        self.stdout.write(f"Import errors count:     {len(summary.import_errors)}")

        if summary.import_errors:
            self.stdout.write(self.style.ERROR("Errors encountered:"))
            for err in summary.import_errors:
                self.stdout.write(self.style.ERROR(f"  - {err}"))
        else:
            self.stdout.write(self.style.SUCCESS("All rows successfully processed without silent drops!"))

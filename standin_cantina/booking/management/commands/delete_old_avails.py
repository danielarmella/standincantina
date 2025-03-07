from django.core.management.base import BaseCommand
from datetime import date, timedelta
from cantina.models import Avail

class Command(BaseCommand):
    help = "Deletes Avails that are older than 3 years."

    def handle(self, *args, **kwargs):
        threshold_date = date.today() - timedelta(days=3*365)  # 3 years ago
        old_avails = Avail.objects.filter(end_date__lt=threshold_date)

        count, _ = old_avails.delete()
        self.stdout.write(self.style.SUCCESS(f"Deleted {count} old Avail records."))
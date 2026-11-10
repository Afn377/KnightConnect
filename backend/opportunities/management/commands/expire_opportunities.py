from django.core.management.base import BaseCommand

from core.maintenance import expire_opportunities


class Command(BaseCommand):
    help = (
        "Close open opportunities whose expiry has passed (reason 'expired') and expire "
        "their pending requests. Schedule this, or call /api/internal/maintenance/ from cron."
    )

    def handle(self, *args, **options):
        count = expire_opportunities()
        noun = "opportunity" if count == 1 else "opportunities"
        self.stdout.write(f"Expired {count} {noun}.")

from django.core.management.base import BaseCommand

from listings.models import Category

CATEGORIES = [
    "Vehicles",
    "Houses",
    "Houses for rent",
    "Land",
    "Electronics",
    "Job offers",
    "Home materials",
    "Fashion",
    "Musical instruments",
    "Sports materials",
    "Agricultural",
    "Kids",
    "Others",
]


class Command(BaseCommand):
    help = "Creates the starting set of categories."

    def handle(self, *args, **options):
        for order, name in enumerate(CATEGORIES):
            category, created = Category.objects.get_or_create(
                name=name, defaults={"order": order}
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f"Created category: {name}"))
            else:
                self.stdout.write(f"Already exists: {name}")

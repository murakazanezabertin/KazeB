import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Category",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=100, unique=True)),
                ("slug", models.SlugField(blank=True, max_length=110, unique=True)),
                ("icon", models.ImageField(blank=True, null=True, upload_to="categories/")),
                ("order", models.PositiveIntegerField(default=0, help_text="Lower numbers appear first.")),
            ],
            options={
                "verbose_name_plural": "categories",
                "ordering": ["order", "name"],
            },
        ),
        migrations.CreateModel(
            name="Listing",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=150)),
                ("description", models.TextField()),
                ("condition", models.CharField(choices=[("new", "New"), ("used", "Used")], default="used", max_length=10)),
                ("district", models.CharField(max_length=100)),
                ("sector", models.CharField(max_length=100)),
                ("price", models.DecimalField(decimal_places=2, max_digits=12)),
                ("is_active", models.BooleanField(default=True, help_text="Uncheck to hide this listing without deleting it.")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "category",
                    models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="listings", to="listings.category"),
                ),
                (
                    "seller",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="listings", to=settings.AUTH_USER_MODEL),
                ),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="ListingImage",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("image", models.ImageField(upload_to="listings/")),
                ("is_cover", models.BooleanField(default=False, help_text="Shown first in the listings grid.")),
                (
                    "listing",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="images", to="listings.listing"),
                ),
            ],
        ),
    ]

import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models

import trust.models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("listings", "0003_listing_currency"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Report",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "reason",
                    models.CharField(
                        choices=[
                            ("scam", "Uburiganya"),
                            ("inappropriate", "Ntibyemewe"),
                            ("wrong_category", "Ubwoko butariho"),
                            ("already_sold", "Byamaze kugurwa"),
                            ("other", "Ikindi"),
                        ],
                        max_length=20,
                    ),
                ),
                ("details", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("is_resolved", models.BooleanField(default=False)),
                ("resolution_notes", models.TextField(blank=True)),
                (
                    "listing",
                    models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="reports", to="listings.listing"),
                ),
                (
                    "reported_user",
                    models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="reports_received", to=settings.AUTH_USER_MODEL),
                ),
                (
                    "reporter",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="reports_filed", to=settings.AUTH_USER_MODEL),
                ),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="Review",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("rating", models.PositiveSmallIntegerField(choices=[(1, "1"), (2, "2"), (3, "3"), (4, "4"), (5, "5")])),
                ("comment", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "reviewer",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="reviews_given", to=settings.AUTH_USER_MODEL),
                ),
                (
                    "seller",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="reviews_received", to=settings.AUTH_USER_MODEL),
                ),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddConstraint(
            model_name="review",
            constraint=models.UniqueConstraint(fields=("reviewer", "seller"), name="one_review_per_seller"),
        ),
        migrations.CreateModel(
            name="PhoneVerification",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("code", models.CharField(max_length=6)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("expires_at", models.DateTimeField(default=trust.models.default_expiry)),
                ("is_verified", models.BooleanField(default=False)),
                ("attempts", models.PositiveSmallIntegerField(default=0)),
                (
                    "user",
                    models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="phone_verification", to=settings.AUTH_USER_MODEL),
                ),
            ],
        ),
    ]
